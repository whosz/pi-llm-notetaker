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
| **C. ReSpeaker 2-Mics Pi HAT** (~$20–30) | medium | ⭐⭐ | GPIO hat: **2 microphones + button + 3 RGB LEDs (APA102) + speaker output, all in one** on paper. On a Keyestudio clone: **speaker output confirmed working**, but **mic capture doesn't work** (see below) — parked, use option A for the microphone instead |

> 💡 **Current plan:** option C's HAT for its speaker output (confirmed working) +
> option A (USB mic) for the microphone, since the HAT's own mics aren't producing
> audio on this board (see the write-up below) and the DNP jack on Seeed's schematic
> means there's likely no external mic input on this HAT either.
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
5. **✅ Confirmed audible** — the board has two independent output paths (its own
   `'Speaker'` and `'Headphone'` mixer controls, matching the WM8960's SPK_* vs HP_*
   pins). Both are live simultaneously by default. To get sound out of the HAT's
   **speaker connector only** (not the headphone jack):
   ```bash
   amixer -c N sset 'Headphone' 0%        # mute headphone/headset output
   amixer -c N sset 'Speaker' 100%        # max speaker volume
   amixer -c N sset 'Speaker DC' 5        # Class-D boost, max (both 0-5 range)
   amixer -c N sset 'Speaker AC' 5
   ```
   If that's still not loud enough: there's a **separate digital `'Playback'` gain
   stage** (the DAC volume, upstream of the analog Speaker path above) that defaults
   to 84%, not 100% — `amixer -c N sset 'Playback' 100%` gives real extra headroom.
   A generated test melody, and a full ~38s piano MIDI file rendered with `timidity`,
   both played back correctly and audibly from the speaker only.
   Persist with `sudo alsactl store` once you're happy with the mixer settings, so
   they survive a reboot (replace `N` above with the card number from `aplay -l`).

**⚠️ Known issue, parked: mic capture doesn't produce real audio — use a USB mic
(option A) instead.** Everything reasonable was tried remotely, none of it worked:

- Correct input pins per Seeed's own schematic (LINPUT1/RINPUT1 → MIC1/MIC2) — confirmed
  by pulling the actual `.sch` PDF, not guessed
- Max gain on every stage: input boost (+29 dB), ADC capture gain (+30 dB), all six
  boost-mixer inputs (LINPUT1/2/3, RINPUT1/2/3) enabled simultaneously, not just the
  correct pair
- Powering the HAT separately via its own micro-USB port, in case GPIO-only power
  wasn't enough for the analog/mic-bias side
- Recording in stereo and inspecting the left and right channels **separately** (in
  case a mono downmix was hiding a working channel) — both channels showed the exact
  same flat, non-speech-correlated noise floor (~100–190/32768, no variation whether
  someone was talking or not)
- Considered installing the board-specific `seeed-voicecard` driver instead of the
  generic `wm8960-soundcard` overlay (which is written for a different physical board —
  see below) — decided against it given the kernel version gap (its newest branch
  targets v6.13, we're on 6.18.x) once a USB mic became the simpler path forward
- The schematic's only external-audio-input footprint (`AUDIO-JACK-8P-SMD`, an 8-pin
  combo jack) is marked **DNP** (Do Not Populate) in Seeed's design — so there may not
  be a 3.5 mm mic input on this board at all to plug an external mic into, clone or not

Output and input share the same codec/overlay/I2C bus, and output works perfectly, so
this is specifically a capture-path (mic bias? board wiring?) issue, not a general
driver or connectivity problem.

Card number also isn't stable across boots (seen both as card 2 and card 3) — resolve
it fresh each time with `aplay -l`/`arecord -l`, don't hardcode it.

**Hypothesis #1, disproven:** originally suspected the `wm8960-soundcard` overlay was
written for a *different* board and routed wrong. Diffed it against Seeed's own
original `seeed-2mic-voicecard-overlay.dts` — the mic routing is **byte-identical**
(`LINPUT1`/`LINPUT3`/`RINPUT1`/`RINPUT2` → `"Mic Jack"` in both). Not the cause.

**Hypothesis #2, tried, made it worse:** a 2025 comment on
[raspberrypi/linux#4384](https://github.com/raspberrypi/linux/issues/4384) (a near-identical
"WM8960 + ReSpeaker capture is garbage" report) points out that routing connects the mic
to *four* boost-mixer inputs (LINPUT1/3, RINPUT1/2) when the board's schematic only
wires two (LINPUT1/RINPUT1) — theory being the other two float and inject noise. Also no
`MICBIAS` control is exposed anywhere in `amixer -c N controls` output, on this driver.
Tested the theory directly: decompiled the live `.dtbo` (`dtc -I dtb -O dts`), rebuilt a
variant overlay with only `LINPUT1`/`RINPUT1` routed (dropped `LINPUT3`/`RINPUT2`),
loaded it as a separate `dtoverlay=` (not overwriting the working one — easy to revert).
Result: **worse, not better** — full-scale clipping (RMS ~6000–12000/32768) in complete
silence, even with input boost gain at 0. That's not amplified noise, it's a different
failure mode entirely (self-oscillation or a DAPM power-sequencing glitch from removing
those paths) — reverted immediately, back to the original overlay/config.

Confirming the mic-bias/wiring theory for real needs either the board-specific
`seeed-voicecard` driver (**still capped at kernel v6.13** as of this check — no v6.14+
branch exists despite the repo's landing page implying otherwise, verified against the
GitHub API's branch list directly) once it catches up, or hands-on measurement
(multimeter on the mic bias/input pins) — not further blind remote overlay surgery.
**Decision unchanged: USB microphone for stage 6's STT input; keep the HAT for its
confirmed-working speaker output.** Revisit later if useful (e.g. a wake-word mic
array), not blocking.

**Considered and rejected: downgrading the kernel to v6.13** to run the real
`seeed-voicecard` driver instead of the generic overlay. Decided against it —
Raspberry Pi OS doesn't treat kernel downgrades as a first-class supported path (no
plain `apt install` to an older version; would mean pinning archived packages or
`rpi-update` to a specific old commit, both explicitly discouraged for anything but
throwaway testing), it's a 5-minor-version jump back that could destabilize things
that *are* working today (SPI/LEDs, `lgpio`/`rpi-lgpio` for GPIO, both systemd units,
the boot-race fix — all verified against the current kernel, none re-verified against
an old one), and even after all that there's no guarantee it actually fixes capture on
this specific clone board. The only upside would be dropping the USB dongle — cosmetic,
not functional. Not a good trade for a system that's currently working end-to-end.

One more data point before giving up on the HAT's own input: plugging a wired headset
mic into the HAT's audio jack (the pins the overlay's own routing table maps to
`"Mic Jack"` — see the hypothesis above) gave the **exact same flat noise floor** as
the onboard mics, on both channels, across native `hw:` recording at multiple sample
rates and durations (ruling out `plughw`/mono-downmix/rate/duration as causes on the
*recording* side too). Same symptom with a completely different, known-good mic source
points at the ADC/capture path itself, not specifically at the onboard mic wiring.

### ✅ Confirmed working: USB microphone (option A)

A cheap USB mic (a Sony SingStar USB mic, i.e. a generic USB Audio Class device) just
works — no overlay, no driver, no config.txt changes:

```bash
arecord -l                          # → new card, e.g. "card 4: U032712189 [USBMIC ...]"
amixer -c 4 sset 'Mic' 100%         # default capture level is ~56%, too quiet
arecord -D plughw:4,0 -d 5 -f S16_LE -r 16000 -c 1 test.wav
```
(replace `4` with whatever card number `arecord -l` shows). Real, speech-correlated
amplitude (thousands, dynamically varying) confirmed by ear and by inspecting the
recorded samples — a completely different signature from the flat HAT noise floor.

**Full pipeline tested end-to-end**, using this USB mic: record → transcribe with
[Vosk](https://alphacephei.com/vosk/) (`vosk-model-small-pl-0.22`, installed via
`uv run --with vosk`, no venv needed) → classify the transcript through Ollama
(`qwen2.5:1.5b`, same `/api/chat` call as `docs/02-local-llm.md`). Spoken "zakup mleko
i chleb" → `{"type": "shopping", "title": "Zakup mleka i chlebu", "items": ["mleko",
"chleb"]}` — correct. Note: the model got it wrong (unrelated hallucinated content) on
2 of 3 attempts with our bare-bones test prompt (no few-shot examples) — expected per
`CLAUDE.md`'s "the model can return garbage" caveat, and exactly why plan stage 2 calls
for few-shot examples and defensive retry-on-failure parsing, not a pipeline bug.

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

- [x] `arecord -l` sees the microphone; test recording actually captures audio — true
      with a **USB mic** (see above); the HAT's onboard mics still don't, parked
- [x] `aplay` plays sound on the selected output — confirmed audible, out of the
      HAT's **speaker** connector specifically (headphone output muted), see step 5 above
- [ ] The button changes state (test with a gpiozero script); the RGB LED shows red, green,
      and blue individually, then does `.pulse()` — confirms wiring and cathode/anode polarity
      (N/A if using the HAT's own button/LEDs — that's separate SPI/GPIO work, still open)
- [x] The STT model is downloaded and tested on a recording — Vosk PL, full pipeline
      (mic → Vosk → Ollama) verified end-to-end, see above
- [ ] Piper speaks a test sentence: `echo "Hi, this is your Pi" | piper ... | aplay`

Next: plan stages [06 (voice service)](../plan/06-voice-service.md) and [07 (wizard)](../plan/07-setup-wizard.md)
