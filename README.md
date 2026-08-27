# 🗒️ PiLLm Note Taker — a smart note catcher for Raspberry Pi 4

A note-taking and organizing system that runs **entirely locally on a Raspberry Pi 4**:

- 🎙️ Press a physical button on the Pi and say a note out loud — an LED and a sound
  give feedback while it's listening — or 📝 type a note on the web page
- 🧠 A local LLM (Ollama) classifies and structures it: *shopping list, quote, idea, task, meeting…*
- 🌐 Notes land on a website hosted on the Pi (browsing, editing, lists)
- 📅 Selected types sync to Google: **Calendar** (meetings) and **Tasks** (lists/tasks)

## Status

| Stage | What | State |
|---|---|---|
| 1–3 | Backend, LLM pipeline, web frontend | ✅ Done |
| 5 | Deploy: both services auto-start on boot (`systemd`) | 🟡 Partial — backup/nginx/`/healthz` still open, see [docs/05-deployment.md](docs/05-deployment.md) |
| 6 | Voice: button → record → STT → LLM | 🟡 Prototype only (`voice/button_listen_demo.py`) — press-and-record for a fixed 10s, **no wake word, no TTS, no state machine** yet |
| 4, 7 | Google sync, setup wizard | ⬜ Not started |

The button-triggered voice flow works end-to-end on real hardware (Keyestudio/ReSpeaker
2-Mics HAT + a USB mic — the HAT's own onboard mics don't work, see
[docs/06-voice-and-hardware.md](docs/06-voice-and-hardware.md)) and survives a reboot,
but it's explicitly a stepping stone toward stage 6, not stage 6 itself.

## Architecture

```
┌───────────────────────────── Raspberry Pi 4 ─────────────────────────────┐
│                                                                          │
│  🎙️ microphone  🔘 button  💡 LED  🔊 speaker                            │
│        │           │          ▲          ▲                               │
│  ┌─────┴───────────┴──────────┴──────────┴─────┐                         │
│  │ Voice service (separate process)             │                         │
│  │ wake word → recording → STT → feedback (TTS) │                         │
│  └──────────────────┬──────────────────────────┘                         │
│                     │ POST /api/notes                                    │
│  ┌──────────┐   ┌───▼───────────┐   ┌─────────────┐   ┌──────────┐      │
│  │ Frontend │──▶│ Backend       │──▶│ Ollama      │   │ SQLite   │      │
│  │ (web +   │◀──│ FastAPI       │◀──│ (local      │   │ (DB)     │      │
│  │  wizard) │   │ :8000         │   │  LLM :11434)│   └────▲─────┘      │
│  └──────────┘   │               │   └─────────────┘        │            │
│                 │  Google Sync ─┼────────────────────┐     │            │
│                 └───────────────┴─────────────────────┼────┘            │
└───────────────────────────────────────────────────────┼─────────────────┘
                                                        ▼
                                        Google Calendar API / Tasks API
```

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| LLM | [Ollama](https://ollama.com) + a small model (e.g. `qwen2.5:1.5b`, `llama3.2:3b`) | Works offline on ARM64, simple API |
| Wake word | [openWakeWord](https://github.com/dscripka/openWakeWord) | Local, lightweight, custom phrase |
| STT / TTS | [Vosk](https://alphacephei.com/vosk/) / [Piper](https://github.com/rhasspy/piper) | Real-time on Pi 4, offline |
| GPIO | [gpiozero](https://gpiozero.readthedocs.io) | Button + LED (fade) with no boilerplate |
| Backend | Python 3.11 + [FastAPI](https://fastapi.tiangolo.com) | Lightweight, async, great docs |
| Database | SQLite | Zero configuration, ideal for a Pi |
| Frontend | Jinja2 + [HTMX](https://htmx.org) + [Basecoat](https://basecoatui.com) | shadcn/ui look, vendored plain HTML/CSS/JS — no React/node at runtime |
| Google | `google-api-python-client` (Calendar + Tasks) | Official libraries |
| Deploy | systemd + (optionally) nginx + [Tailscale](https://tailscale.com) | Autostart, secure remote access |

## Repository structure

```
pi-llm-notetaker/
├── README.md                     ← this file
├── CLAUDE.md                     ← instructions for Claude Code (conventions, stack, constraints)
├── docs/                         ← device setup documentation (for you)
│   ├── 01-pi-setup.md
│   ├── 02-local-llm.md
│   ├── 03-architecture.md
│   ├── 04-google-integration.md
│   ├── 05-deployment.md
│   └── 06-voice-and-hardware.md  ← microphone, button, LED, wake word, TTS
└── plan/                         ← implementation plan for Claude Code (by stage)
    ├── 00-stages-overview.md
    ├── 01-backend-database.md
    ├── 02-llm-pipeline.md
    ├── 03-frontend.md
    ├── 04-google-sync.md
    ├── 05-deploy.md
    ├── 06-voice-service.md       ← voice assistant (separate process)
    └── 07-setup-wizard.md        ← first-run setup wizard
```

## Getting started

1. Set up the Pi per [docs/01-pi-setup.md](docs/01-pi-setup.md)
2. Install Ollama and a model per [docs/02-local-llm.md](docs/02-local-llm.md)
3. Open the project in **Claude Code** and work through the stages in [plan/00-stages-overview.md](plan/00-stages-overview.md)
4. Set up the Google API per [docs/04-google-integration.md](docs/04-google-integration.md)
5. Deploy as systemd services per [docs/05-deployment.md](docs/05-deployment.md)
6. Connect the microphone, button, and LED per [docs/06-voice-and-hardware.md](docs/06-voice-and-hardware.md),
   then plan stages 6–7 — you'll do the rest of the configuration through the **browser-based wizard**

## License

MIT (change as you see fit).
