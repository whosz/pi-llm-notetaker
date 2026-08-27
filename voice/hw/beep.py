"""Short beep tones for start/end-of-recording audio feedback.

Synthesized in memory (stdlib only, no disk writes — the SD card dislikes
frequent writes) and piped straight into `aplay`. Playback is best-effort:
if the speaker isn't available, we log and move on rather than crash the
voice pipeline over cosmetics.
"""

import io
import math
import re
import struct
import subprocess
import wave

RATE = 16000


def _tone(freq: float, duration: float, volume: float = 0.28) -> bytes:
    """Synthesize a mono 16-bit PCM sine tone as WAV bytes."""
    n = int(RATE * duration)
    frames = b"".join(
        struct.pack("<h", int(volume * 32767 * math.sin(2 * math.pi * freq * t / RATE)))
        for t in range(n)
    )
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(frames)
    return buf.getvalue()


START_BEEP = _tone(880, 0.15)  # short high tone: "listening started"
END_BEEP = _tone(440, 0.15)  # short lower tone: "listening stopped"


def find_hat_speaker_device() -> str | None:
    """Card numbers shift across reboots — look up the HAT's wm8960 sound
    card by name instead of hardcoding it. None if not present."""
    result = subprocess.run(
        ["aplay", "-l"], capture_output=True, text=True, check=False
    )
    match = re.search(r"card (\d+): .*wm8960", result.stdout, re.IGNORECASE)
    return f"plughw:{match.group(1)},0" if match else None


def play(wav_bytes: bytes, device: str | None) -> None:
    if device is None:
        return
    subprocess.run(["aplay", "-q", "-D", device, "-"], input=wav_bytes, check=False)
