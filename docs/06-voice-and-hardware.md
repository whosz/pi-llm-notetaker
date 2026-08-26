# 06 — Voice and hardware (microphone, button, LED, sound)

Goal: the Pi listens for a wake phrase (like "OK Google"), but **only when listening
mode is turned on with a physical button**. An LED and sound give full feedback:
standby → activation → recording → accepted / error.

## Important thing to know up front: the Pi has no audio input

The Raspberry Pi **has no analog microphone input** — you can't plug a mic straight
into the pins like an LED. Realistic options (from simplest):

| Option | Cost | Difficulty | Notes |
|---|---|---|---|
| **A. USB microphone** | ~$10–20 | ⭐ easy | Zero soldering or configuration. E.g. a mini USB mic or a conference mic with noise cancellation. **Recommended starting point.** |
| **B. I2S microphone on GPIO pins** (e.g. **INMP441**, ~$5) | cheap | ⭐⭐⭐ | "Real" wiring to the pins, requires overlay configuration and sometimes soldering headers |
| **C. ReSpeaker 2-Mics Pi HAT** (~$20–30) | medium | ⭐⭐ | GPIO hat: **2 microphones + button + 3 RGB LEDs (APA102) + speaker output, all in one**. Perfectly covers this project's requirements. **Partially working** on a Keyestudio clone (see below) — card enumerates and mixer is controllable, but mic capture is not yet producing real audio |

> 💡 If you want minimum hassle — **option C (ReSpeaker HAT)** gives you everything
> this project needs right away (microphone, button, LEDs, audio out).
> If you like building it yourself — option A (USB mic) + button and LED from the table below.
> 📚 [ReSpeaker 2-Mics Pi HAT documentation](https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/)

### Option C in practice: Keyestudio/ReSpeaker 2-Mics HAT, mainline overlay (no driver compile)

Tested on a **Keyestudio 5V ReSpeaker 2-Mic Pi HAT V1.0** (a hardware-compatible clone of
Seeed's ReSpeaker 2-Mics Pi HAT — same WM8960 codec) on Raspberry Pi OS / Debian 13
"trixie", kernel `6.18.x`.

The community driver (`respeaker/seeed-voicecard`, or the `HinTak/seeed-voicecard` fork
recommended for newer Debian) builds an out-of-tree kernel module per kernel version —
as of writing, its newest ready-made branch targets kernel **v6.13**, several versions
behind what current Raspberry Pi OS ships. Rather than fight a DKMS build against a
kernel it wasn't updated for (or fall back to `--compat-kernel`, which downgrades the
kernel package), **use the `wm8960-soundcard` overlay that ships in Raspberry Pi's own
firmware** — same WM8960 codec chip, zero compilation:

1. Add to `/boot/firmware/config.txt`:
   ```ini
   dtoverlay=wm8960-soundcard
   ```
2. `sudo reboot`
3. Confirm the card shows up for **both** playback and capture:
   ```bash
   aplay -l   # → card N: wm8960soundcard [wm8960-soundcard], ...
   arecord -l # → same card, capture side
   ```
4. **Gotcha:** the codec's internal DAC→output routing switches default to **off**, so
   the speaker/headphone output stays silent even at full volume until you enable them:
   ```bash
   amixer -c N sset 'Left Output Mixer PCM' on
   amixer -c N sset 'Right Output Mixer PCM' on
   ```
   (replace `N` with the card number from `aplay -l`; persist with `sudo alsactl store`
   once you're happy with the mixer settings, so it survives a reboot)

**⚠️ Open issue: mic capture is not producing real audio.** The card enumerates
correctly for capture and the mixer is fully controllable (confirmed via `amixer -c N`),
but recordings are digital silence (`max≈3/32768`) after a brief power-on transient in
the first ~1 second, regardless of speech, volume, mic input boost (+29 dB), or ADC
capture gain (+30 dB) — all tried, none changed the result. Also tried powering the HAT
separately via its onboard micro-USB port (in case GPIO-only power wasn't enough for
the analog/mic-bias side) — no change. The speaker output path (see the gotcha above)
was fixed and a test tone played with no ALSA errors, but this hasn't been confirmed
audible by ear either.

Card number also isn't stable across boots (seen both as card 2 and card 3) — resolve
it fresh each time with `aplay -l`/`arecord -l`, don't hardcode it.

Current hypothesis: the Keyestudio clone may differ from Seeed's original ReSpeaker
schematic in a way the generic `wm8960-soundcard` overlay (built for a different board,
Waveshare's WM8960 HAT) doesn't account for — e.g. mic bias routing. Needs a hands-on
session (multimeter on the mic bias/input pins) rather than further blind remote mixer
tweaking. Not blocking — plan stage 6 (this HAT's button + LEDs) is unstarted anyway.

This overlay only covers **audio** (both mics + speaker output) — it does not know
about the HAT's physical **button** or its **3 APA102 RGB LEDs**, which are a separate
SPI/GPIO subsystem unrelated to the WM8960 codec. Wiring/driving those is still open —
see plan stage 6.

## Audio output (signals + voice feedback)

- Simplest: Pi's **3.5 mm jack** → a small powered speaker (active)
- Alternatively: an I2S amplifier **MAX98357A** (~$3) + a 3 W speaker (pins: BCLK→GPIO18,
  LRC→GPIO19, DIN→GPIO21) — 📚 [Adafruit MAX98357A guide](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/raspberry-pi-usage)
- The ReSpeaker HAT has its own speaker output (JST) and jack

⚠️ You can't combine two I2S devices (INMP441 mic + MAX98357A amp) "for free" on the
same clock pins — this is the most common source of frustration.
Trouble-free combos: **USB mic + jack** or **ReSpeaker HAT**.

## Button and LED — wiring diagram (options A/B)

Parts: momentary tact switch, a **4-leg RGB LED** (common cathode or common anode),
3× **330 Ω** resistor (one per color leg), wires.

> 💡 A 4-leg RGB LED is actually three LEDs (red, green, blue) sharing one common leg.
> The common leg is usually the **longest** one. To find out cathode vs. anode without
> guessing: touch a 3 V source (e.g. 2×AA) through a 330 Ω resistor across the common leg
> and one color leg — if it lights up with the resistor+battery **−** on the common leg,
> it's common cathode (far more common in hobby kits); if it needs **+** on the common
> leg, it's common anode.

| Part | GPIO | Physical pin | Wiring |
|---|---|---|---|
| Button (toggle listening mode) | **GPIO17** | pin 11 | one leg → GPIO17, the other → GND (pin 9); internal pull-up in software |
| RGB LED — red leg | **GPIO27** (soft PWM) | pin 13 | GPIO27 → 330 Ω resistor → red leg |
| RGB LED — green leg | **GPIO22** (soft PWM) | pin 15 | GPIO22 → 330 Ω resistor → green leg |
| RGB LED — blue leg | **GPIO23** (soft PWM) | pin 16 | GPIO23 → 330 Ω resistor → blue leg |
| RGB LED — common leg | — | — | **common cathode:** straight to GND (pin 14) · **common anode:** straight to 3.3V (pin 1) — no resistor on this leg |

These three GPIOs are free either way and don't collide with the button or with either
I2S option below.

INMP441 I2S microphone (option B only):

| INMP441 | Pi | Physical pin |
|---|---|---|
| VDD | 3.3V | pin 1 |
| GND | GND | pin 6 |
| SCK | GPIO18 | pin 12 |
| WS  | GPIO19 | pin 35 |
| SD  | GPIO20 | pin 38 |
| L/R | GND | (left channel) |

Configuration in `/boot/firmware/config.txt`: `dtparam=i2s=on` + microphone overlay.
📚 Tutorials: [pinout.xyz (pin map)](https://pinout.xyz) ·
[INMP441 on Raspberry Pi (I2S mic guide, Adafruit)](https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test) ·
[gpiozero — Button and RGBLED](https://gpiozero.readthedocs.io/en/stable/recipes.html)

## LED behavior (UX contract)

With an RGB LED, color carries meaning too, not just the pattern:

| State | Color | Pattern | Sound |
|---|---|---|---|
| Listening mode **off** | — | off | — |
| Standby (listening for wake phrase) | white/blue | gentle "breathing" (fade 0→30% every ~3 s) | — |
| Wake phrase detected → recording | blue | clear fade/pulse 0→100% | short "ding" at the start |
| Processing (STT + LLM) | amber/yellow | fast blinking | — |
| ✅ Accepted | green | 2 s solid light | voice confirmation: "Added to your shopping list" |
| ❌ Error / not understood | red | 3 short flashes | voice message: "Didn't catch that, try again" |

(Exact hues aren't load-bearing — pick whatever reads clearly on your specific LED;
what matters is that each state is visually distinct.)

## Audio software stack (sized for the Pi 4's capabilities)

| Function | Tool | Why |
|---|---|---|
| Wake phrase | **[openWakeWord](https://github.com/dscripka/openWakeWord)** | Fully local, ~a few % of one core, **you can train your own phrase for free with a notebook** (link in the project repo). Alternative: [Porcupine](https://picovoice.ai/platform/porcupine/) (easier custom-phrase training via a web console, free for personal use, needs a key) |
| End-of-speech detection (VAD) | **[Silero VAD](https://github.com/snakers4/silero-vad)** | Tiny model, trims the recording once you stop talking |
| Speech recognition (STT) | **[Vosk](https://alphacephei.com/vosk/)** — pick a model matching the language you'll speak to it (e.g. `vosk-model-small-en-us-0.15`, ~40 MB, or the Polish `vosk-model-small-pl-0.22`, ~50 MB) | Runs in real time on a Pi 4. Alternative for better quality: [whisper.cpp](https://github.com/ggml-org/whisper.cpp) `base` (more accurate, but a few to a dozen seconds per note) |
| Speech synthesis (TTS, feedback) | **[Piper](https://github.com/rhasspy/piper)** + a voice matching your language (e.g. `en_US`) | Faster than real-time on a Pi 4, natural-sounding voice, offline |
| Sound cues | pre-made WAV files + `aplay` | Zero CPU, instant |
| GPIO (button, LED) | **gpiozero** | Standard on the Pi, `Button` + `RGBLED` (3 soft-PWM channels, `.color = (r, g, b)`, `.pulse()`, `.blink()`) handle the fade and color; pass `active_high=False` for a common-anode LED |

## Power budget — how it all fits on a Pi 4 (crucial!)

Rule: **only one heavy thing runs at a time**, and the chain is sequential:

```
standby:     openWakeWord (light, continuous)     ~10–15% CPU
   ↓ phrase detected → STOP wake-word listening
recording:   audio capture + Silero VAD            negligible
   ↓ silence → recording ends
STT:         Vosk (small model)                    ~1–3 s, 1 core
   ↓ text → POST to the backend (existing notes pipeline)
LLM:         Ollama (as before, in the background) a few to a dozen seconds
   ↓ result
TTS:         Piper — short message                 <1 s
   ↓ voice feedback + LED → back to standby
```

Additional performance rules (implemented in plan stage 6):

- The voice service is a **separate process** (its own systemd unit) — audio issues never
  block the website
- The "accepted" feedback is spoken **right after STT+LLM classification**, without waiting
  for the Google sync (which runs in the background regardless)
- Button off = wake word doesn't run at all (zero CPU on audio)
- Vosk/Piper models are loaded once at service startup and kept in RAM
  (~200–300 MB combined — with 4 GB RAM pick the `qwen2.5:0.5b` or `1.5b` LLM)

## Shopping list ("build it yourself" option)

- [ ] USB microphone (or INMP441 + header pins)
- [ ] Tact switch button + 4-leg RGB LED + 3× 330 Ω resistor
- [ ] Female-to-female jumper wires (dupont) + a breadboard for testing
- [ ] Small active speaker with a 3.5 mm jack (or MAX98357A + 3 W speaker)

## Checklist

- [x] `arecord -l` sees the microphone (card enumerates) — ⚠️ but recorded audio is
      silence, see the open issue above; not actually working yet
- [ ] `aplay` plays sound on the selected output — mixer routing fixed (see gotcha
      above) and test tone played with no ALSA errors, but not confirmed audible
- [ ] The button changes state (test with a gpiozero script); the RGB LED shows red, green,
      and blue individually, then does `.pulse()` — confirms wiring and cathode/anode polarity
      (N/A if using the HAT's own button/LEDs — that's separate SPI/GPIO work, still open)
- [ ] The STT model is downloaded and tested on a recording
- [ ] Piper speaks a test sentence: `echo "Hi, this is your Pi" | piper ... | aplay`

Next: plan stages [06 (voice service)](../plan/06-voice-service.md) and [07 (wizard)](../plan/07-setup-wizard.md)
