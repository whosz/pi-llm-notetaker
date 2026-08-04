# Stage 6 — Voice service (wake word, recording, feedback)

## Goal

A separate `voice/` process (its own systemd unit) that: once enabled via the button,
listens for the wake phrase → gives a signal (ding + LED fade) → records the command →
STT → sends the text to the backend like a regular note → speaks feedback (Piper) and
signals the result with the LED. Hardware and stack: `docs/06-voice-and-hardware.md`.

## Architecture

```
voice/
├── main.py          # main loop + state machine
├── config.py        # reads config shared with the backend (see below)
├── hw/
│   ├── button.py    # gpiozero Button (GPIO from config), mode toggle, debounce
│   ├── led.py       # gpiozero RGBLED: idle_breath / listening_pulse / processing_blink / ok / error,
│   │                # each state = a (color, pattern) pair per docs/06-voice-and-hardware.md
│   └── audio.py     # recording (sounddevice/alsa), WAV playback, device selection
├── wake.py          # openWakeWord (phrase model path from config)
├── stt.py           # Vosk streaming + Silero VAD (end of speech)
├── tts.py           # Piper: cache generated fixed phrases on disk!
└── client.py        # POST /api/notes + polling for the classification result (max ~30 s)
```

State machine: `OFF → IDLE → TRIGGERED → RECORDING → TRANSCRIBING → SUBMITTING → FEEDBACK → IDLE`
(+ `ERROR` from any state). States map 1:1 to the LED behaviors and sounds
in the table in `docs/06-voice-and-hardware.md` — that table is the UX contract, stick to it.

## Shared configuration

The voice service reads settings saved by the wizard (stage 7) from the backend:
`GET /api/settings` on startup + refresh on a signal (SIGHUP) or simple polling
every 60 s. Keys include: `wake_word_model_path`, `mic_device`, `output_device`,
`gpio_button`, `gpio_led_red`, `gpio_led_green`, `gpio_led_blue`, `volume`, `stt_engine`,
`tts_voice`, `feedback_phrases`.
Until the wizard exists, values come from `.env` (same names).

## Tasks

1. `hw/` modules + a diagnostic script `voice/selftest.py`
   (LED → sound → 3 s recording → playback → button state); the selftest result is
   also exposed via the API for the wizard
2. `wake.py` — openWakeWord on the microphone stream; sensitivity threshold from config;
   support for a custom phrase model (an `.onnx`/`.tflite` file referenced in settings)
3. `stt.py` — Vosk (model from config) + Silero VAD: recording ends after
   ~1.2 s of silence or a hard 30 s cap
4. `tts.py` — Piper; **fixed phrases generated once and cached as WAV files**
   ("Didn't catch that…", "Added to your shopping list", etc.) — instant playback;
   dynamic phrases (note title) generated on the fly
5. `client.py` + feedback logic:
   - success: a message depending on the type ("Added to your shopping list: milk, bread",
     "Saved the meeting for Friday at 3pm")
   - timeout/still processing: "Saved it, processing in the background" (the note is in the DB regardless!)
   - network/backend error: an error message + 3 LED flashes
6. Resilience: no microphone/audio device at startup → the service logs an error,
   the LED signals an error every 10 s, the process **doesn't** crash-loop
7. `deploy/pi-llm-notetaker-voice.service` (After=pi-llm-notetaker.service, Restart=on-failure,
   `SupplementaryGroups=audio gpio`)
8. Tests: the state machine and feedback logic with mocked hw/wake/stt/tts
   (hw modules sit behind interfaces so they're testable without hardware)

## Performance rules (enforced in code)

- Wake word disabled (button OFF) = **zero** active audio streams
- During RECORDING/TRANSCRIBING, wake word is stopped (never two audio models at once)
- Vosk/openWakeWord/Piper models are loaded once at process startup
- The process runs with `nice 5` — the web server and Ollama take priority

## Acceptance criteria

- [ ] A full scenario without touching the keyboard: button ON → wake phrase → ding + pulse →
      "add milk and bread to shopping" → shortly after, a voice: "Added to your shopping list…",
      the note visible on the site
- [ ] Button OFF → `htop` shows no audio activity from the service
- [ ] Unplugging the microphone → error signaled, the service keeps running once reconnected
- [ ] Unintelligible speech → a voice message + 3 flashes, no empty note created
- [ ] The website stays responsive during transcription (the separate process does its own thing)
- [ ] `pytest -q` green without hardware
