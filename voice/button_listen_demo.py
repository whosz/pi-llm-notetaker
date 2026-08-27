"""Minimal demo: press the HAT's button (GPIO17) -> record for a fixed
duration from a USB mic -> transcribe with Vosk -> POST the text to the app
as a new note (which the stage-2 pipeline then classifies automatically).

This is a **prototype**, not the real stage 6 voice service — no wake word,
no LED feedback, no TTS, no state machine. Just to try out button + mic + LLM
together. See plan/06-voice-service.md for the real thing.

Usage (on the Pi):
    uv run --with gpiozero --with vosk python3 voice/button_listen_demo.py

Requires: a Vosk model at ~/voice-test/model (see docs/06-voice-and-hardware.md),
a USB microphone (the HAT's own mics don't work, see the same doc), and the
app running at API_URL.
"""

import json
import os
import re
import subprocess
import wave

import httpx
from gpiozero import Button
from vosk import KaldiRecognizer, Model

BUTTON_GPIO = 17
RECORD_SECONDS = 10
VOSK_MODEL_PATH = os.path.expanduser("~/voice-test/model")
API_URL = "http://localhost:8000/api/notes"
RECORDING_PATH = "/tmp/button_note.wav"


def find_usb_mic_device() -> str:
    """Card numbers shift across reboots/replugs — look it up instead of
    hardcoding it."""
    result = subprocess.run(
        ["arecord", "-l"], capture_output=True, text=True, check=True
    )
    match = re.search(r"card (\d+): .*USB Audio", result.stdout)
    if not match:
        raise RuntimeError("No USB microphone found in `arecord -l` output")
    return f"plughw:{match.group(1)},0"


def record(device: str, path: str, seconds: int) -> None:
    subprocess.run(
        [
            "arecord",
            "-D",
            device,
            "-d",
            str(seconds),
            "-f",
            "S16_LE",
            "-r",
            "16000",
            "-c",
            "1",
            path,
        ],
        check=True,
    )


def transcribe(path: str, model: Model) -> str:
    with wave.open(path, "rb") as wf:
        rec = KaldiRecognizer(model, wf.getframerate())
        parts = []
        while True:
            data = wf.readframes(4000)
            if not data:
                break
            if rec.AcceptWaveform(data):
                parts.append(json.loads(rec.Result()).get("text", ""))
        parts.append(json.loads(rec.FinalResult()).get("text", ""))
    return " ".join(p for p in parts if p).strip()


def main() -> None:
    device = find_usb_mic_device()
    print(f"Using microphone: {device}")
    model = Model(VOSK_MODEL_PATH)

    button = Button(BUTTON_GPIO, bounce_time=0.1)
    print(
        f"Ready. Press the button (GPIO{BUTTON_GPIO}) to record a {RECORD_SECONDS}s note."
    )

    def on_press() -> None:
        print("Button pressed — recording...")
        record(device, RECORDING_PATH, RECORD_SECONDS)
        print("Transcribing...")
        text = transcribe(RECORDING_PATH, model)
        if not text:
            print("(heard nothing)")
            return
        print(f"Heard: {text!r}")
        resp = httpx.post(API_URL, json={"text": text}, timeout=10)
        print(f"Saved as note {resp.json().get('id')} (status {resp.status_code})")

    button.when_pressed = on_press

    import signal

    signal.pause()


if __name__ == "__main__":
    main()
