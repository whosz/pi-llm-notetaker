# 05 — Deployment on the Pi (production)

Goal: the app starts on its own after a Pi reboot, is reachable from your devices,
and has backups.

## systemd service for the app

The `deploy/pi-llm-notetaker.service` file (created in plan stage 5) is installed like this:

```bash
sudo cp deploy/pi-llm-notetaker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pi-llm-notetaker
```

Draft contents:

```ini
[Unit]
Description=PiLLm Note Taker web app
After=network.target ollama.service
Wants=ollama.service

[Service]
User=pi
WorkingDirectory=/home/pi/pi-llm-notetaker
ExecStart=/home/pi/pi-llm-notetaker/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Logs: `journalctl -u pi-llm-notetaker -f`

📚 Tutorial: [DigitalOcean — systemd essentials](https://www.digitalocean.com/community/tutorials/systemd-essentials-working-with-services-units-and-the-journal)

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
uv sync                      # install any new dependencies
sudo systemctl restart pi-llm-notetaker
```

## Final checklist

- [ ] `sudo reboot` → after 2 minutes the site works with no manual action
- [ ] `systemctl status pi-llm-notetaker pi-llm-notetaker-voice ollama` — all services `active (running)`
- [ ] Site reachable from your phone (Tailscale, and/or `https://notes.yourdomain.com` if public)
- [ ] If public: `curl -I https://notes.yourdomain.com` without credentials returns `401`
- [ ] Backup in cron, restored once as a test
- [ ] A "test meeting tomorrow at noon" note shows up in Google Calendar
