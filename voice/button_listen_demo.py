"""Minimal demo: press the HAT's button (GPIO17) -> record for a fixed
duration from a USB mic -> transcribe with Vosk -> POST the text to the app
as a new note (which the stage-2 pipeline then classifies automatically).

This is a **prototype**, not the real stage 6 voice service — no wake word,
no TTS, no state machine. Has LED + start/end beep feedback while recording.
See plan/06-voice-service.md for the real thing.

Usage (on the Pi, from the repo root):
    PYTHONUNBUFFERED=1 uv run --with gpiozero --with vosk --with lgpio --with apa102-pi \
        python3 -m voice.button_listen_demo

Run as `-m voice.button_listen_demo` (not as a bare script path) so the
`voice.hw.leds` import resolves. PYTHONUNBUFFERED matters when redirecting
output to a log file (e.g. via nohup/setsid) — otherwise print() output sits
in a block buffer and doesn't show up until it fills, making the script look
hung.

Requires: a Vosk model at ~/voice-test/model (see docs/06-voice-and-hardware.md),
a USB microphone (the HAT's own mics don't work, see the same doc), the app
running at API_URL, and SPI enabled (`dtparam=spi=on`, then reboot) for the
HAT's onboard LEDs — LEDs degrade to a no-op if unavailable.
"""

import json
import os
import subprocess
import wave

import httpx
from gpiozero import Button
from vosk import KaldiRecognizer, Model

from voice.hw.audio_devices import find_usb_mic_device, wait_for_device
from voice.hw.beep import END_BEEP, START_BEEP, find_hat_speaker_device, play
from voice.hw.leds import RecordingIndicator

BUTTON_GPIO = 17
RECORD_SECONDS = 10
VOSK_MODEL_PATH = os.path.expanduser("~/voice-test/model")
API_URL = "http://localhost:8000/api/notes"
RECORDING_PATH = "/tmp/button_note.wav"


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
    device = wait_for_device(find_usb_mic_device, "USB microphone")
    if device is None:
        raise SystemExit("No USB microphone found (arecord -l) after 30s — giving up.")
    print(f"Using microphone: {device}")
    speaker = wait_for_device(find_hat_speaker_device, "HAT speaker", timeout=10)
    print(f"Using speaker: {speaker or '(none found — beeps disabled)'}")
    model = Model(VOSK_MODEL_PATH)

    button = Button(BUTTON_GPIO, bounce_time=0.1)
    print(
        f"Ready. Press the button (GPIO{BUTTON_GPIO}) to record a {RECORD_SECONDS}s note."
    )

    def on_press() -> None:
        print("Button pressed — recording...")
        play(START_BEEP, speaker)
        with RecordingIndicator():
            record(device, RECORDING_PATH, RECORD_SECONDS)
        play(END_BEEP, speaker)
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
