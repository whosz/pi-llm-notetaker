# Stage 2 — LLM pipeline (background note classification)

## Goal

Every new note is automatically classified and structured by the local Ollama model,
**asynchronously in the background** — the HTTP request never waits for the LLM.

## Tasks

1. `app/llm/client.py` — async Ollama client (httpx):
   - `POST {OLLAMA_URL}/api/chat` with `"stream": false, "format": "json"`
   - 120 s timeout, 1 retry on network error; errors never crash the app
2. `app/llm/prompts.py` — the classifier's system prompt:
   - the JSON contract from `docs/03-architecture.md` (type, title, items, datetime, due, confidence)
   - **current date and weekday included in the prompt** (handling "tomorrow", "on Friday at 3")
   - 2–3 few-shot examples (shopping, meeting, quote)
3. `app/llm/parser.py` — defensive parsing:
   - strip any ``` fences → `json.loads` → Pydantic validation
   - error → retry once with the error message attached; second failure → fallback
     `type=note`, `confidence=0`, status `processed` (see CLAUDE.md)
4. Background worker:
   - simplest approach: `asyncio.Queue` + a task started in the app's lifespan,
     processed **one at a time** (the Pi can't handle parallel generations)
   - on app startup: pick up any leftover `pending` notes from the DB
   - result: update the note (type, title, payload, status); for `shopping`,
     create `list_items` records
5. Extend the `shopping` logic: if an active shopping list from the last 24 h
   exists — append items to it instead of creating a new note
6. Tests: the Ollama client is **mocked** (respx/monkeypatch); separate parser tests
   against malicious inputs (incomplete JSON, wrong type, garbage around the JSON)
7. `scripts/test_llm.py` — a manual test against a live Ollama instance (run on the Pi):
   you provide text, you get back the classified JSON + execution time

## Acceptance criteria

- [ ] `POST /api/notes` returns immediately (<100 ms), and after a few to a dozen seconds
      `GET /api/notes/{id}` shows `status=processed` with the type filled in
- [ ] "buy milk and 2x bread" → `type=shopping`, 2 items in `list_items`
- [ ] "meeting with Anna tomorrow at 3pm" → `type=meeting`, correct date in `payload.datetime`
- [ ] Killing Ollama mid-request → the note ends up `status=error` with a message, the app stays up
- [ ] `pytest -q` green (without a running Ollama)
