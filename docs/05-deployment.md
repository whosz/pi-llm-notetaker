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

**Recommendation: Tailscale instead of exposing the Pi to the internet.**
No open ports, encrypted, works on your phone. After installation
(see [01-pi-setup.md](01-pi-setup.md)) the site is reachable at
`http://pi-llm-notetaker:8000` from any of your devices on the tailnet.

Bonus: [Tailscale HTTPS / MagicDNS](https://tailscale.com/kb/1153/enabling-https) gives you
a free certificate, so you can add the site "to the home screen" on your phone like a PWA.

### Optional: nginx as a reverse proxy

Only needed once you want port 80/443, compression, and serving static files without Python:

```bash
sudo apt install -y nginx
sudo cp deploy/nginx-pi-llm-notetaker.conf /etc/nginx/sites-available/pi-llm-notetaker
sudo ln -s /etc/nginx/sites-available/pi-llm-notetaker /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

📚 Tutorial: [nginx reverse proxy — documentation](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)

> If you still want access from the public internet without a VPN — use
> [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
> (free, no port opening needed). In that case **make sure** to add authentication
> (Cloudflare Access, or the additional plan stage: in-app login).

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
- [ ] Site reachable from your phone (Tailscale)
- [ ] Backup in cron, restored once as a test
- [ ] A "test meeting tomorrow at noon" note shows up in Google Calendar
