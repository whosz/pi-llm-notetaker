from app.llm.parser import parse_classification
from app.llm.worker import process_note
from app.models import ListItem, Note


def test_parse_valid_json():
    result = parse_classification(
        '{"type": "shopping", "title": "Milk", "items": ["milk"], "confidence": 0.9}'
    )
    assert result is not None
    assert result.type == "shopping"
    assert result.items == ["milk"]


def test_parse_code_fenced_json():
    raw = '```json\n{"type": "quote", "title": "x"}\n```'
    result = parse_classification(raw)
    assert result is not None
    assert result.type == "quote"


def test_parse_garbage_returns_none():
    assert parse_classification("not json at all") is None


def test_parse_wrong_type_field_returns_none():
    assert parse_classification('{"type": "bogus-type"}') is None


async def test_worker_classifies_shopping_note(client, monkeypatch):
    async def fake_classify(system_prompt, note_text):
        return '{"type": "shopping", "title": "Groceries", "items": ["milk", "bread"], "confidence": 0.9}'

    monkeypatch.setattr("app.llm.worker.classify", fake_classify)

    resp = await client.post("/api/notes", json={"text": "buy milk and bread"})
    note_id = resp.json()["id"]

    await process_note(note_id, session_maker=client.session_maker)

    resp = await client.get(f"/api/notes/{note_id}")
    data = resp.json()
    assert data["status"] == "processed"
    assert data["type"] == "shopping"
    assert data["title"] == "Groceries"
    assert [i["text"] for i in data["items"]] == ["milk", "bread"]


async def test_worker_merges_into_recent_shopping_note(client, monkeypatch):
    async def fake_classify(system_prompt, note_text):
        return '{"type": "shopping", "title": "Groceries", "items": ["eggs"], "confidence": 0.9}'

    monkeypatch.setattr("app.llm.worker.classify", fake_classify)

    async with client.session_maker() as session:
        existing = Note(
            raw_text="buy milk", type="shopping", title="Groceries", status="processed"
        )
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        existing_id = existing.id

    resp = await client.post("/api/notes", json={"text": "buy eggs too"})
    new_id = resp.json()["id"]

    await process_note(new_id, session_maker=client.session_maker)

    resp = await client.get(f"/api/notes/{existing_id}")
    assert [i["text"] for i in resp.json()["items"]] == ["eggs"]

    resp = await client.get(f"/api/notes/{new_id}")
    data = resp.json()
    assert data["items"] == []
    assert data["payload"]["merged_into_note_id"] == existing_id


async def test_worker_dedupes_items_on_merge(client, monkeypatch):
    async def fake_classify(system_prompt, note_text):
        return '{"type": "shopping", "title": "Groceries", "items": ["Milk", "eggs"], "confidence": 0.9}'

    monkeypatch.setattr("app.llm.worker.classify", fake_classify)

    async with client.session_maker() as session:
        existing = Note(
            raw_text="buy milk", type="shopping", title="Groceries", status="processed"
        )
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        existing_id = existing.id
        session.add(ListItem(note_id=existing_id, text="milk", position=0))
        await session.commit()

    resp = await client.post("/api/notes", json={"text": "milk and eggs"})
    new_id = resp.json()["id"]

    await process_note(new_id, session_maker=client.session_maker)

    resp = await client.get(f"/api/notes/{existing_id}")
    assert [i["text"] for i in resp.json()["items"]] == ["milk", "eggs"]


async def test_worker_falls_back_to_note_type_on_repeated_garbage(client, monkeypatch):
    async def fake_classify(system_prompt, note_text):
        return "not valid json"

    monkeypatch.setattr("app.llm.worker.classify", fake_classify)

    resp = await client.post("/api/notes", json={"text": "some rambling text"})
    note_id = resp.json()["id"]

    await process_note(note_id, session_maker=client.session_maker)

    resp = await client.get(f"/api/notes/{note_id}")
    data = resp.json()
    assert data["status"] == "processed"
    assert data["type"] == "note"
    assert data["payload"]["confidence"] == 0.0


async def test_worker_marks_error_when_ollama_unreachable(client, monkeypatch):
    from app.llm.client import OllamaError

    async def fake_classify(system_prompt, note_text):
        raise OllamaError("connection refused")

    monkeypatch.setattr("app.llm.worker.classify", fake_classify)

    resp = await client.post("/api/notes", json={"text": "anything"})
    note_id = resp.json()["id"]

    await process_note(note_id, session_maker=client.session_maker)

    resp = await client.get(f"/api/notes/{note_id}")
    data = resp.json()
    assert data["status"] == "error"
    assert "connection refused" in data["error_msg"]
