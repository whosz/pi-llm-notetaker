# Stage 1 — Backend skeleton and database

## Goal

A working FastAPI API backed by SQLite: full CRUD for notes and list items, no LLM yet
(notes stay in `pending` status for now).

## Tasks

1. Project initialization:
   - `pyproject.toml` (managed by `uv`), dependencies: fastapi, uvicorn,
     sqlalchemy[asyncio], aiosqlite, pydantic, pydantic-settings, jinja2, httpx (dev: pytest, pytest-asyncio, ruff)
   - `.gitignore` (incl. `.env`, `credentials.json`, `token.json`, `*.db`, `.venv`)
   - `.env.example` with the full set of variables and comments
2. `app/config.py` — settings from `.env` (DB path, Ollama URL, model name,
   sync flags — unused for now)
3. `app/db.py` + `app/models.py` — async engine, **SQLite in WAL mode**, models
   `Note`, `ListItem`, `SyncLog` matching `docs/03-architecture.md`;
   schema is created at app startup (Alembic migrations are premature at this point)
4. `app/schemas.py` — Pydantic schemas (NoteCreate, NoteOut, ListItemOut, …)
5. `app/routers/notes.py` — endpoints:
   - `POST /api/notes` → 202, saved with `status=pending`
   - `GET /api/notes` (filters: `type`, `q` — simple LIKE, `limit/offset` pagination)
   - `GET /api/notes/{id}`, `PATCH /api/notes/{id}`, `DELETE /api/notes/{id}`
   - `PATCH /api/items/{id}` (checked)
6. Pytest tests for every endpoint (in-memory DB / temp file)

## Out of scope for this stage

Ollama calls, HTML, Google — none of that is touched yet.

## Acceptance criteria

- [ ] `uvicorn app.main:app` starts without errors, `/docs` shows all endpoints
- [ ] `curl -X POST /api/notes -d '{"text":"test"}'` returns 202 with an id; the note is visible in `GET /api/notes`
- [ ] The database file runs in WAL mode (`PRAGMA journal_mode;` → `wal`)
- [ ] `pytest -q` green, `ruff check .` clean
