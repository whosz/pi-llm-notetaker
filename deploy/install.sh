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

sudo cp deploy/pi-llm-notetaker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pi-llm-notetaker

systemctl status --no-pager pi-llm-notetaker
