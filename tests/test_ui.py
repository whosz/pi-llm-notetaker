from app.models import ListItem, Note


async def test_home_page(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "New note" in resp.text


async def test_add_note_returns_card_fragment(client):
    resp = await client.post("/notes", data={"text": "buy milk"})
    assert resp.status_code == 200
    assert "buy milk" in resp.text
    assert 'id="note-' in resp.text


async def test_note_card_polls_while_pending(client):
    resp = await client.post("/notes", data={"text": "buy milk"})
    assert "hx-trigger" in resp.text


async def test_shopping_card_renders_items_and_toggle(client):
    async with client.session_maker() as session:
        note = Note(
            raw_text="shop", type="shopping", title="Shopping", status="processed"
        )
        session.add(note)
        await session.flush()
        item = ListItem(note_id=note.id, text="milk", position=0)
        session.add(item)
        await session.commit()
        note_id, item_id = note.id, item.id

    resp = await client.get(f"/notes/{note_id}/card")
    assert resp.status_code == 200
    assert "milk" in resp.text

    resp = await client.post(f"/items/{item_id}/toggle")
    assert resp.status_code == 200
    assert "checked" in resp.text
    assert "line-through" in resp.text


async def test_edit_and_delete_note(client):
    resp = await client.post("/notes", data={"text": "original"})
    note_id = resp.text.split('id="note-')[1].split('"')[0]

    resp = await client.patch(f"/notes/{note_id}", data={"raw_text": "edited"})
    assert resp.status_code == 200
    assert "edited" in resp.text

    resp = await client.delete(f"/notes/{note_id}")
    assert resp.status_code == 200

    resp = await client.get(f"/notes/{note_id}/card")
    assert resp.status_code == 404


async def test_search_filters_notes_list(client):
    await client.post("/notes", data={"text": "buy milk"})
    await client.post("/notes", data={"text": "call dentist"})

    resp = await client.get("/notes-list", params={"q": "milk"})
    assert "buy milk" in resp.text
    assert "call dentist" not in resp.text
