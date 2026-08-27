# 05 — Deployment on the Pi (production)

Goal: the app starts on its own after a Pi reboot, is reachable from your devices,
and has backups.

## systemd services

Two units, both in `deploy/`, both installed the same way:

```bash
cd ~/pi-llm-notetaker
./deploy/install.sh
```

`install.sh` is idempotent — safe to re-run after every `git pull`. It runs `uv sync`
(+ `uv sync --group voice` for the hardware libs), copies both unit files, and does
`enable --now` on each. Adjust `User=`/`WorkingDirectory=` in the unit files first if
your Pi user or clone path isn't `matt` / `/home/matt/pi-llm-notetaker`.

### `pi-llm-notetaker.service` — the web app

```ini
[Unit]
Description=PiLLm Note Taker web app
After=network.target ollama.service
Wants=ollama.service

[Service]
User=matt
WorkingDirectory=/home/matt/pi-llm-notetaker
ExecStart=/home/matt/pi-llm-notetaker/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### `pi-llm-notetaker-voice.service` — the button demo (prototype)

Runs `voice/button_listen_demo.py` (see that file's docstring — it's explicitly a
prototype: press-and-record, no wake word, no TTS, not the real stage 6 service).
Needs its own dependency group and, for the LEDs, SPI enabled — see
[06-voice-and-hardware.md](06-voice-and-hardware.md) for the hardware side.

```ini
[Unit]
Description=PiLLm Note Taker button->mic->LLM demo (prototype, see voice/button_listen_demo.py)
After=network.target pi-llm-notetaker.service sound.target
Wants=pi-llm-notetaker.service
StartLimitIntervalSec=300
StartLimitBurst=10

[Service]
User=matt
WorkingDirectory=/home/matt/pi-llm-notetaker
ExecStart=/home/matt/pi-llm-notetaker/.venv/bin/python3 -m voice.button_listen_demo
Restart=on-failure
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Prerequisites this unit needs that `install.sh` does **not** set up for you (one-time,
manual — see [06-voice-and-hardware.md](06-voice-and-hardware.md) for the full story):

- **SPI enabled** for the HAT's onboard LEDs: `sudo raspi-config` (or add
  `dtparam=spi=on` to `/boot/firmware/config.txt`), then reboot. Without it the LEDs
  silently no-op (`voice/hw/leds.py` degrades gracefully) rather than crash.
- `sudo apt install -y swig liblgpio-dev` — the `lgpio` Python package (gpiozero's
  backend on kernels where legacy `RPi.GPIO`/sysfs is broken) compiles a small C
  extension and needs both to build.
- A Vosk model unpacked at `~/voice-test/model` and a USB microphone plugged in (the
  HAT's own onboard mics don't work on this board — see 06).

Logs: `journalctl -u pi-llm-notetaker -f` / `journalctl -u pi-llm-notetaker-voice -f`

📚 Tutorial: [DigitalOcean — systemd essentials](https://www.digitalocean.com/community/tutorials/systemd-essentials-working-with-services-units-and-the-journal)

## Gotchas from initial bring-up (worth knowing before you debug them again)

- **A fresh reboot can look like the voice service "didn't start."** The USB audio
  driver (`snd-usb-audio`) registers surprisingly late — around 20s into boot on this
  Pi (check with `dmesg | grep snd-usb-audio`). `voice/hw/audio_devices.py` polls for
  the mic/speaker for up to 30s/10s instead of failing immediately, specifically so the
  service doesn't burn through systemd's restart budget and land in a permanently
  `failed` state before the hardware exists yet. If you ever see that anyway, `journalctl
  -u pi-llm-notetaker-voice` first — `systemctl show <unit> -p NRestarts,Result` tells
  you if it's crash-looping.
- **After a `sudo reboot`, give the Pi 1–2 minutes before concluding it's dead.** SSH
  refusing the connection (`No route to host`) right after issuing a reboot is normal —
  it's still shutting down/booting, not evidence of a config problem.
- **Journald here is not persistent by default** (`/var/log/journal` exists but nothing
  survives past the current boot — `journalctl --list-boots` only shows boot `0`). If
  you want to debug a boot that already happened, it's too late; run
  `sudo mkdir -p /var/log/journal && sudo systemctl restart systemd-journald` once to
  turn persistence on going forward.
- **An unclean shutdown can lose recent SQLite writes.** WAL mode is crash-*safe*
  (`PRAGMA integrity_check` stays clean), but a `sudo reboot` issued while uvicorn is
  mid-write can still leave the WAL's last committed state short of what you saw a
  moment earlier — we lost a session's worth of test notes this way. Real backups
  (`deploy/backup.sh`, still on the stage-5 TODO list below) are the actual fix; until
  then, don't treat data on the Pi as durable.

## Accessing the site

Two options — use either, or both (Tailscale for admin access even if the site is
also public).

### Private: Tailscale

No open ports, encrypted, works on your phone. After installation
(see [01-pi-setup.md](01-pi-setup.md)) the site is reachable at
`http://pi-llm-notetaker:8000` from any of your devices on the tailnet.

Bonus: [Tailscale HTTPS / MagicDNS](https://tailscale.com/kb/1153/enabling-https) gives you
a free certificate, so you can add the site "to the home screen" on your phone like a PWA.

### Public: router port-forward + nginx + Cloudflare

Notes are personal data, so exposing the app to the internet needs TLS and
authentication in front of it — **neither belongs in the FastAPI app itself**, both
live in nginx.

1. **Router**: forward external `80` and `443` to the Pi's LAN IP. Don't forward `22`
   (SSH) — keep that reachable only over Tailscale/LAN.
2. **Cloudflare DNS**: point an `A` record (e.g. `notes.yourdomain.com`) at your public
   IP, **proxied** (orange cloud) — hides your home IP and adds Cloudflare's edge
   protections for free.
3. **nginx**, installed as a reverse proxy in front of uvicorn:
   ```bash
   sudo apt install -y nginx apache2-utils
   sudo cp deploy/nginx-pi-llm-notetaker.conf /etc/nginx/sites-available/pi-llm-notetaker
   sudo ln -s /etc/nginx/sites-available/pi-llm-notetaker /etc/nginx/sites-enabled/
   ```
4. **TLS**: since Cloudflare already terminates TLS at the edge, skip
   Let's Encrypt/certbot (one less renewal timer to babysit) — generate a free
   **Origin Certificate** in the Cloudflare dashboard (SSL/TLS → Origin Server),
   save it as `/etc/ssl/pi-llm-notetaker/origin.pem` + `origin.key` on the Pi, and
   reference both in the nginx `server` block. Set Cloudflare's SSL/TLS mode to
   **Full (strict)**.
5. **HTTP Basic Auth** — the app never sees credentials, nginx blocks unauthenticated
   requests before they reach it:
   ```bash
   sudo htpasswd -c /etc/nginx/.htpasswd yourusername
   ```
   In the nginx `server` block:
   ```nginx
   auth_basic "PiLLm Note Taker";
   auth_basic_user_file /etc/nginx/.htpasswd;
   ```
   Basic Auth sends credentials base64-encoded on every request — fine over HTTPS
   (Cloudflare + the Origin Certificate), **never** serve it over plain HTTP.
6. **Firewall**: only nginx should be reachable from the internet.
   ```bash
   sudo ufw allow 80,443/tcp
   sudo ufw enable
   ```
   Port 8000 (uvicorn) stays LAN/Tailscale-only — nginx is the only public entry point.
7. `sudo nginx -t && sudo systemctl reload nginx`

📚 Tutorials: [nginx reverse proxy](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/) ·
[Cloudflare Origin CA certificates](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/)

## Backups

The whole database is a single SQLite file — backup is trivial. The `deploy/backup.sh`
script (stage 5) makes a safe copy via `sqlite3 .backup` and keeps the last 14:

```bash
# crontab -e entry (daily at 3:00)
0 3 * * * /home/pi/pi-llm-notetaker/deploy/backup.sh
```

It's worth copying backups off the SD card (a second USB drive / rsync to a NAS / rclone to the cloud).

## Updating the app

```bash
cd ~/pi-llm-notetaker
git pull
./deploy/install.sh          # uv sync (both groups) + reinstall + restart both units
```

Or by hand, if you only touched one side:

```bash
uv sync                                  # web app deps
uv sync --group voice                    # voice demo deps
sudo systemctl restart pi-llm-notetaker pi-llm-notetaker-voice
```

## Current status

Done and verified with a real `sudo reboot` (not just in theory): both units above
come up on their own, `NRestarts=0`, app responds `HTTP 200`. Still open, from the
original stage-5 task list:

- [ ] `deploy/backup.sh` (see the WAL/data-loss gotcha above — this is the real fix)
- [ ] `deploy/nginx-*.conf` + public access (only needed if you want the site reachable
      off your LAN/Tailscale)
- [ ] `GET /healthz`
- [ ] Security review (note length limit, security headers)

## Final checklist

- [x] `sudo reboot` → after 1–2 minutes the site and voice demo work with no manual action
- [x] `systemctl status pi-llm-notetaker pi-llm-notetaker-voice ollama` — all services `active (running)`
- [ ] Site reachable from your phone (Tailscale, and/or `https://notes.yourdomain.com` if public)
- [ ] If public: `curl -I https://notes.yourdomain.com` without credentials returns `401`
- [ ] Backup in cron, restored once as a test
- [ ] A "test meeting tomorrow at noon" note shows up in Google Calendar
