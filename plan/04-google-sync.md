# Stage 4 — Google sync (Calendar + Tasks)

## Goal

`meeting` notes land in Google Calendar, and `shopping`/`task` notes land in Google Tasks —
automatically after classification (if sync is enabled) and manually via a button.

## Prerequisites (done by the user, not Claude Code)

Google Cloud setup per `docs/04-google-integration.md`: APIs enabled,
`credentials.json` in the project directory. The code should assume the file might
not exist (sync disabled = the app works normally).

## Tasks

1. Dependencies: `google-api-python-client`, `google-auth-oauthlib`
2. `scripts/google_auth.py` — a one-time **headless** authorization (console flow):
   prints a URL, accepts a code, saves `token.json`; token refresh handled
   in `app/sync/auth.py` (auto-refresh, clear error when the token has expired)
3. `app/sync/calendar.py`:
   - `create_event(note)` → `events.insert` (title, start from `payload.datetime`,
     60 min by default, description = `raw_text`, 30-min popup reminder)
   - store `external_id` in `sync_log`; syncing the same note again → `events.update`
4. `app/sync/tasks.py`:
   - ensure the lists exist ("Shopping", "PiLLm Note Taker") — `tasklists.list` / `insert`
   - `shopping` → items as `tasks.insert` on the "Shopping" list
   - `task` → a task with `due`
   - idempotent via `sync_log` (no duplicates on retry)
5. Hook into the pipeline: after `processed`, when `GOOGLE_SYNC_ENABLED=true` and the
   type is sync-eligible → a sync job on the same background queue; sync errors
   **never** affect the note's own status (separate status in `sync_log` + a UI badge)
6. Endpoint `POST /api/notes/{id}/sync` + a "📤 Send to Google" button on the card
7. Retry with backoff on 429/5xx errors from Google (max 3 attempts)
8. Tests: Google clients fully mocked; idempotency test

## Privacy note

Only notes of type meeting/shopping/task ever go to Google, and only when sync is
enabled. Quotes/ideas/notes never leave the Pi. Don't change this without an explicit
request from the user.

## Acceptance criteria

- [ ] "dentist appointment on Thursday at 5pm" → an event visible in Google Calendar
      with a reminder
- [ ] A shopping note → items on the "Shopping" list in Google Tasks (phone/Gmail)
- [ ] Manually syncing the same note twice doesn't create duplicates
- [ ] Missing `credentials.json` / `GOOGLE_SYNC_ENABLED=false` → the app runs with no
      errors in the logs
- [ ] `pytest -q` green with no network access
