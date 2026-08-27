#!/usr/bin/env bash
# Idempotent: installs/updates the systemd unit and (re)starts the app.
# Run from the repo root on the Pi: ./deploy/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env"  # puts uv on PATH

if ! systemctl is-enabled --quiet ollama 2>/dev/null; then
  echo "warning: ollama.service not found/enabled — the app will start but classification will fail" >&2
fi

uv sync
uv sync --group voice  # Pi-only hardware libs (gpiozero, vosk, lgpio, apa102-pi, rpi-lgpio)

sudo cp deploy/pi-llm-notetaker.service deploy/pi-llm-notetaker-voice.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pi-llm-notetaker pi-llm-notetaker-voice

systemctl status --no-pager pi-llm-notetaker pi-llm-notetaker-voice
