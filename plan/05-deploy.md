# Stage 5 — Deployment and maintenance

## Goal

Everything starts on its own after a Pi reboot, data has backups, and the project has
setup documentation that matches reality.

## Tasks

1. `deploy/` directory:
   - `pi-llm-notetaker.service` — systemd unit (drafted in `docs/05-deployment.md`):
     `After=ollama.service`, restart on-failure, runs from `.venv`
   - `backup.sh` — `sqlite3 <db> ".backup <file>"` + 14-copy rotation + `gzip`
   - `nginx-pi-llm-notetaker.conf` — reverse proxy (proxy_pass to :8000, serve
     `/static/` directly); if public access is enabled, also carries the
     `auth_basic` directive and the Cloudflare Origin Certificate `ssl_certificate`
     lines described in `docs/05-deployment.md` — nginx owns TLS and auth, the app
     never sees either
   - `install.sh` — an idempotent install script for a fresh Pi:
     checks Ollama, creates a venv (`uv sync`), copies the unit, enables+starts it
2. Health check: `GET /healthz` — app, database, and Ollama status (`/api/tags`);
   wired into the unit as a simple post-start check
3. Logging: levels via `.env` (`LOG_LEVEL`), logs to stdout → journald
   (no custom log files — save the SD card)
4. Update `README.md`: a "Step-by-step Pi installation" section reflecting the
   final state (commands from `install.sh`)
5. Security review:
   - the app listens on `0.0.0.0`, but is only reachable directly over Tailscale/LAN —
     if publicly exposed (see `docs/05-deployment.md`), nginx is the only public entry
     point (port 8000 stays firewalled from the internet), and it's the one enforcing
     TLS + `auth_basic`; the app itself never implements login/OAuth
   - headers: `X-Content-Type-Options`, a sensible CSP for local assets
   - a note length limit (e.g. 10,000 characters) — protects against accidentally
     pasting a huge block of text into the LLM

## Acceptance criteria

- [ ] `deploy/install.sh` on a clean Pi results in a working app
- [ ] `sudo reboot` → the site and classification work with no manual intervention
- [ ] `backup.sh` produces a valid copy (restored to a file and opened with sqlite3 as a test)
- [ ] `/healthz` reports the status of every component
- [ ] The README has current, complete installation instructions
