from app.models import ListItem


async def test_create_and_get_note(client):
    resp = await client.post("/api/notes", json={"text": "buy milk and bread"})
    assert resp.status_code == 202
    note = resp.json()
    assert note["status"] == "pending"
    assert note["raw_text"] == "buy milk and bread"

    resp = await client.get("/api/notes")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get(f"/api/notes/{note['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == note["id"]


async def test_get_missing_note_404(client):
    resp = await client.get("/api/notes/999")
    assert resp.status_code == 404


async def test_update_note(client):
    resp = await client.post("/api/notes", json={"text": "original"})
    note_id = resp.json()["id"]

    resp = await client.patch(f"/api/notes/{note_id}", json={"title": "New title"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New title"


async def test_delete_note(client):
    resp = await client.post("/api/notes", json={"text": "temp"})
    note_id = resp.json()["id"]

    resp = await client.delete(f"/api/notes/{note_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/notes/{note_id}")
    assert resp.status_code == 404


async def test_filter_notes_by_query(client):
    await client.post("/api/notes", json={"text": "buy milk"})
    await client.post("/api/notes", json={"text": "call dentist"})

    resp = await client.get("/api/notes", params={"q": "milk"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert "milk" in results[0]["raw_text"]


async def test_update_list_item(client):
    resp = await client.post("/api/notes", json={"text": "shopping note"})
    note_id = resp.json()["id"]

    async with client.session_maker() as session:
        item = ListItem(note_id=note_id, text="milk", position=0)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        item_id = item.id

    resp = await client.patch(f"/api/items/{item_id}", json={"checked": True})
    assert resp.status_code == 200
    assert resp.json()["checked"] is True


async def test_update_missing_item_404(client):
    resp = await client.patch("/api/items/999", json={"checked": True})
    assert resp.status_code == 404
