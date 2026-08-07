# CLAUDE.md — instructions for Claude Code

This file is read automatically by Claude Code at the start of a session.
It describes the project context, conventions, and hard constraints.

## What this project is

PiLLm Note Taker (pi-llm-notetaker): a note-taking system running entirely on a **Raspberry Pi 4 (ARM64, 4–8 GB RAM)**.
The user types a loose note → a local LLM (Ollama) classifies and structures it →
the note is stored in SQLite and shown on a web page → selected types sync to
Google Calendar / Google Tasks. The device also has a voice assistant mode:
a physical button enables listening for a wake word, after which the Pi records the
command (STT: Vosk), and gives feedback via voice (TTS: Piper) and an LED (stages 6–7 of the plan).

The implementation plan is split into stages in the `plan/` directory. **Work through one
stage at a time**, in numeric order. Each stage has acceptance criteria — don't move on
until they're met.

## Hard constraints (Raspberry Pi 4!)

- **Little RAM and a slow CPU.** No heavy dependencies: no node/webpack/React in the build,
  no Postgres, no Docker (unless the user asks). Frontend = Jinja2 + HTMX + Basecoat
  (shadcn/ui's design system reimplemented as plain HTML/CSS + a small vanilla-JS file —
  no React, no Node runtime, no build step: see the Stack section below).
- **The LLM is slow** (a few tokens/s). Ollama calls are always asynchronous, with a timeout
  (120 s minimum) and queuing — never block the HTTP request on generation time.
  Pattern: the endpoint accepts the note → saves it to the DB with status `pending` → a
  background task classifies it → status `processed`. The frontend polls via HTMX.
- **The model can return garbage.** Parse LLM responses defensively: force JSON in the prompt,
  strip any ```json fences, validate with Pydantic, fall back to type `note` on error.
- The SD card dislikes frequent writes: SQLite in WAL mode, no unnecessary disk logging.
- **Audio never runs in the web server process.** The voice service is a separate process
  (`voice/`, its own systemd unit), talking to the backend only over HTTP. At most one
  audio model runs at a time (wake word OR STT), models are loaded once at startup,
  fixed TTS phrases are cached as WAV files. Button OFF = zero active audio streams.
- GPIO/audio code always sits behind interfaces with a fake implementation — tests must pass
  without hardware and without a microphone.

## Stack and conventions

- Python 3.11+, FastAPI, SQLAlchemy 2.0 (async) + aiosqlite, Pydantic v2, Jinja2, HTMX,
  [Basecoat](https://basecoatui.com) (shadcn/ui components ported to plain HTML/CSS/JS —
  npm package `basecoat-css`, used only as a source of vendored static files, never as a
  runtime or build dependency of the app).
- Dependency management: `uv` (fallback: `pip` + `requirements.txt`).
- Code structure:
  ```
  app/
  ├── main.py            # FastAPI app, routers
  ├── config.py          # settings from .env (pydantic-settings)
  ├── db.py              # engine, sessions, migrations
  ├── models.py          # SQLAlchemy models
  ├── schemas.py         # Pydantic schemas
  ├── llm/               # Ollama client + prompts + parsing
  ├── sync/               # Google integration (calendar.py, tasks.py, auth.py)
  ├── routers/            # endpoints (notes.py, lists.py, sync.py, ui.py)
  ├── templates/          # Jinja2, incl. templates/basecoat/ (vendored component macros)
  └── static/             # app.css (ours), htmx.min.js, static/basecoat/ (vendored CSS+JS,
                           #   mirrors the basecoat-css package's own dist/ layout)
  voice/                  # separate voice assistant process (stage 6)
  ├── main.py            # state machine OFF→IDLE→…→FEEDBACK
  ├── hw/                # button, led, audio (gpiozero, behind interfaces)
  ├── wake.py stt.py tts.py client.py
  ```
- HTMX, Basecoat's CSS/JS, and any other frontend asset are kept **locally** in `static/`
  (the Pi must work without internet access) — fetch them once from the CDN or npm package
  during development and commit the built files, never load them from a CDN at runtime.
- Secrets only in `.env` (in `.gitignore`). The repo keeps a `.env.example`.
- Tests: pytest + httpx; Ollama and Google calls are always mocked in tests.
- Comments, code identifiers, and UI text (templates) are all in English.

## Commands

- Run dev server: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Tests: `pytest -q`
- Lint/format: `ruff check . && ruff format .`

## What NOT to do

- Don't add login/session/OAuth logic to the FastAPI app itself. Access control is
  handled outside the app: Tailscale for private access, or nginx (`auth_basic` +
  a Cloudflare Origin Certificate) in front of it for public access — see
  `docs/05-deployment.md`.
- Don't send note contents to any external API other than the explicitly configured Google APIs.
- Don't commit `credentials.json`, `token.json`, or `.env`.
- Don't optimize prematurely — get the working vertical slice first (stages 1–3), then integrations.
