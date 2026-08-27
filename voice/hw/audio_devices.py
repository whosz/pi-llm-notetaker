"""ALSA device lookup, with a bounded retry for boot-time races.

Pure stdlib (no gpiozero/vosk) so this stays importable — and testable —
without the Pi-only hardware dependencies.
"""

import re
import subprocess
import time
from collections.abc import Callable


def find_usb_mic_device() -> str | None:
    """Card numbers shift across reboots/replugs — look it up instead of
    hardcoding it."""
    result = subprocess.run(
        ["arecord", "-l"], capture_output=True, text=True, check=True
    )
    match = re.search(r"card (\d+): .*USB Audio", result.stdout)
    return f"plughw:{match.group(1)},0" if match else None


def wait_for_device(
    lookup: Callable[[], str | None],
    label: str,
    timeout: float = 30,
    interval: float = 1,
) -> str | None:
    """The USB audio driver registers ~20s into boot (dmesg: snd-usb-audio
    loads late) — on a fresh reboot this service can easily start before
    the mic/speaker card exists yet. Poll instead of failing immediately,
    so we don't crash-loop and burn through systemd's restart budget before
    the hardware ever becomes ready."""
    deadline = time.monotonic() + timeout
    while True:
        device = lookup()
        if device or time.monotonic() >= deadline:
            return device
        time.sleep(interval)
