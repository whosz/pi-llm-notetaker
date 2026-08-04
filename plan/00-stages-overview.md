# Implementation plan — stage overview

This directory is the work plan for **Claude Code**. Each stage = a separate file = a
separate session (or a few). Work through the stages **in order** — each one ends with a
working, testable increment.

## How to work with Claude Code

1. Clone the repo to your working machine (dev) — on the Pi you pull via `git pull`.
   You can also work directly on the Pi over SSH (Claude Code runs in the terminal).
2. In the project directory, run `claude`
3. Start a stage with a prompt like:

   > Read CLAUDE.md and plan/01-backend-database.md and implement this stage.
   > Work in small steps, running tests after each significant step.

4. At the end of the stage, check the **acceptance criteria** in the stage file, commit,
   and only then move on.

💡 Tips: ask Claude Code for a plan before coding (plan mode — `shift+tab`),
   commit often, and paste full error messages when you hit problems.

📚 [Claude Code documentation](https://docs.claude.com/en/docs/claude-code/overview)

## Stages

| # | File | Scope | Result |
|---|---|---|---|
| 1 | [01-backend-database.md](01-backend-database.md) | FastAPI, SQLite, note CRUD | API works, tests pass |
| 2 | [02-llm-pipeline.md](02-llm-pipeline.md) | Ollama client, background classification | notes get a type and structure on their own |
| 3 | [03-frontend.md](03-frontend.md) | web page (Jinja2+HTMX) | full browser and phone usage |
| 4 | [04-google-sync.md](04-google-sync.md) | Calendar + Tasks | meetings and lists land in Google |
| 5 | [05-deploy.md](05-deploy.md) | systemd, backup, documentation | works on its own after a Pi restart |
| 6 | [06-voice-service.md](06-voice-service.md) | wake word, button, LED, STT, TTS | voice assistant with full feedback |
| 7 | [07-setup-wizard.md](07-setup-wizard.md) | first-run wizard | browser-based configuration, no terminal needed |

Stages 6–7 require hardware and setup from [docs/06-voice-and-hardware.md](../docs/06-voice-and-hardware.md).

## Additional stages (post-MVP, optional)

- **PWA:** manifest + service worker, so the site installs on a phone
- **Login:** simple authentication, if the site needs to go beyond Tailscale
- **Two-way sync:** checking something off in Google Tasks → checked off on the Pi too

## Global rules (apply to every stage)

- Hardware constraints and conventions: see [CLAUDE.md](../CLAUDE.md) — Claude Code reads it automatically
- Architecture and data model: [docs/03-architecture.md](../docs/03-architecture.md)
- Definition of done for a stage: acceptance criteria ✅ + `pytest -q` green + `ruff check` clean
