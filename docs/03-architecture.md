# 03 — System architecture

## Data flow

```
User (browser / phone)
        │  POST /notes  { "text": "buy milk and bread" }
        ▼
┌─ FastAPI (:8000) ─────────────────────────────────────────────┐
│ 1. Save the raw note to SQLite  (status: pending)             │
│ 2. Return 202 + id  (the user doesn't wait for the LLM!)      │
│                                                               │
│ Background worker (asyncio task / queue):                     │
│ 3. POST → Ollama /api/chat  (format: json)                    │
│ 4. Parse + validate the response (Pydantic)                   │
│ 5. Update the note: type, title, items  (processed)           │
│ 6. If type = meeting/task and sync enabled → queue for Google │
└───────────────────────────────────────────────────────────────┘
        │                                    │
        ▼                                    ▼
   SQLite (WAL)                 Google Calendar / Tasks API
```

The frontend (HTMX) polls `/notes/{id}` every 2 s until the status changes to `processed`,
and swaps the note card in place without a page reload.

## Note types (LLM classification)

| Type | Example input | What the system does | Google sync |
|---|---|---|---|
| `shopping` | "buy milk, bread, 2x butter" | creates/appends to a shopping list, items as checkboxes | Google Tasks ("Shopping" list) |
| `meeting` | "meeting with Anna on Friday at 3pm" | extracts date/time/title | Google Calendar (event) |
| `task` | "call the repair shop by Wednesday" | task with a due date | Google Tasks |
| `quote` | "»Simplicity is the ultimate sophistication«" | saved in the quotes collection | — |
| `idea` | "idea: an app for…" | ideas collection | — |
| `note` | everything else / fallback | plain note | — |

## Data model (SQLite)

```
notes
├── id            INTEGER PK
├── raw_text      TEXT        -- original content from the user
├── type          TEXT        -- shopping|meeting|task|quote|idea|note
├── title         TEXT        -- assigned by the LLM
├── payload       JSON        -- type-dependent fields (items[], datetime, due, etc.)
├── status        TEXT        -- pending|processed|error
├── error_msg     TEXT NULL
├── created_at    DATETIME
└── updated_at    DATETIME

list_items                     -- list items (shopping etc.)
├── id, note_id FK, text, checked BOOL, position INT

sync_log                       -- what was sent to Google and when
├── id, note_id FK, target (calendar|tasks), external_id, synced_at, status
```

## LLM contract (draft system prompt)

The backend sends Ollama a system prompt that enforces a structure:

```json
{
  "type": "shopping | meeting | task | quote | idea | note",
  "title": "short title",
  "items": ["shopping only — list of items"],
  "datetime": "ISO 8601 or null — meeting only",
  "due": "ISO 8601 or null — task only",
  "confidence": 0.0
}
```

Resilience rules (implemented in `app/llm/`):

- `"format": "json"` in the Ollama call
- Pydantic validation; validation error → one retry with the error message attached
- second failure → type `note`, status `processed`, `confidence: 0` (a note is never lost)
- current date included in the prompt (the model needs to understand "on Friday", "tomorrow")

## API (draft)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/notes` | new note (returns 202 + id) |
| `GET` | `/api/notes` | list, filters: `type`, `q`, pagination |
| `GET` | `/api/notes/{id}` | details + processing status |
| `PATCH` | `/api/notes/{id}` | edit title/content/type |
| `DELETE` | `/api/notes/{id}` | delete |
| `PATCH` | `/api/items/{id}` | check off a list item |
| `POST` | `/api/notes/{id}/sync` | manually push to Google |
| `GET` | `/` , `/lists`, `/quotes` | HTML views (Jinja2 + HTMX) |

The detailed specification takes shape stage by stage — see the [`plan/`](../plan/00-stages-overview.md) directory.
