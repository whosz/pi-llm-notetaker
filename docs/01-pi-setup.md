# 01 — Preparing the Raspberry Pi 4

Goal: a clean, updated 64-bit system with SSH access, ready for Ollama and the app.

## Hardware requirements

- Raspberry Pi 4 — **8 GB RAM is best** (4 GB also works with a smaller model; 2 GB not recommended)
- microSD card **32 GB min, class A1/A2** (LLM models take 1–3 GB each)
  — even better: an SSD over USB 3.0 (faster and more durable than an SD card)
- Original 5V/3A power supply (underpowered = CPU throttling)
- A heatsink or a case with a fan — the LLM can heat the CPU up quite a bit

## Step 1: Operating system

Install **Raspberry Pi OS Lite (64-bit)** — must be 64-bit, since Ollama doesn't run on 32-bit;
Lite, because a desktop environment just eats RAM the LLM needs.

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Choose: *Raspberry Pi OS (other)* → *Raspberry Pi OS Lite (64-bit)*
3. In the Imager settings (gear icon / Ctrl+Shift+X), configure right away:
   - hostname (e.g. `pi-llm-notetaker`)
   - username and password
   - Wi-Fi (if not using a cable)
   - **enable SSH**

📚 Tutorial: [Getting started — official Raspberry Pi documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html)

## Step 2: First login and update

```bash
ssh your_username@pi-llm-notetaker.local

sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

## Step 3: Basic tools

```bash
sudo apt install -y git curl htop python3-pip python3-venv sqlite3
```

Also install `uv` (a fast Python package manager, used in this project):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

📚 [uv documentation](https://docs.astral.sh/uv/)

## Step 4: Swap memory (important with 4 GB RAM)

LLM models can briefly exceed available RAM. Increase swap to 2 GB:

```bash
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

With 8 GB RAM you can skip this step.

## Step 5: Stable address / convenient access

The simplest and safest remote access option (also from outside your home network): **Tailscale** —
a free mesh VPN, no need to open ports on your router.

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

📚 Tutorial: [Tailscale on Raspberry Pi](https://tailscale.com/kb/1017/install-rpi)

After this step, the Pi is reachable under a stable name (e.g. `pi-llm-notetaker.tailnet-xxxx.ts.net`)
from any of your devices logged into Tailscale.

## Step 6 (optional): temperature monitoring

```bash
vcgencmd measure_temp        # one-off
watch -n 2 vcgencmd measure_temp   # live, during LLM testing
```

If the temperature exceeds ~80°C under load, add cooling — throttling
dramatically slows down token generation.

## Checklist before moving on

- [ ] `uname -m` returns `aarch64` (64-bit system)
- [ ] SSH works
- [ ] `free -h` shows the expected RAM + swap
- [ ] (optional) Tailscale connected

Next: [02-local-llm.md](02-local-llm.md)
