# Stage 7 — First-run setup wizard (on the web page)

## Goal

On first launch, the site walks the user step by step through device configuration
(like setting up a Google Assistant / a new smart speaker): audio, button/LED,
wake phrase, voice, Google. The result is saved in the database (`settings` table),
which the voice service reads from.

## Mechanics

- A new `settings` table (key/value JSON) + `GET/PUT /api/settings`
- A `setup_completed` flag; when `false`, every visit to `/` redirects to `/setup`
- The wizard = HTMX steps (one screen at a time), built with Basecoat components
  (`tabs`/progress indicator, `button` "Back/Next/Skip", `card` per step, `toast` for
  live-test results — see the Basecoat note in `plan/03-frontend.md`)
- Every step has a **live test** — the wizard talks to the voice service through the
  backend (proxy endpoints `POST /api/voice/test/*` → the selftest from stage 6)
- The wizard can be re-run from settings (`/setup?rerun=1`)

## Wizard steps

1. **Welcome** — device name, message language
2. **LLM model** — list of models from Ollama (`/api/tags`), a recommendation based on
   detected RAM; a "download recommended" button with a progress bar
3. **Audio — microphone** — pick a device from a list (`arecord -l` via the API),
   test: "record 3 seconds" → playback in the browser, a signal-level meter
4. **Audio — speaker** — pick an output, a volume slider, a "play test sound" button
5. **Button and LED** — GPIO numbers for the button and the RGB LED's red/green/blue legs
   (default 17 / 27 / 22 / 23, editable), plus a common-cathode/common-anode toggle,
   an interactive test: "press the button now" → ✅ on the page; "cycle the LED" (red →
   green → blue → white) → confirmation
6. **Wake phrase** — the heart of the "custom phrase" requirement:
   - pick a bundled openWakeWord model **or**
   - a custom phrase: step-by-step instructions for training one for free with the
     openWakeWord notebook (📚 link in `docs/06`) + upload the trained model file
     through the wizard form
   - a sensitivity slider + a live tester: "say the phrase now" → a detection counter
7. **Assistant voice** — pick a Piper voice (listen to samples), edit the feedback text
   (e.g. what it should say after adding items to the shopping list)
8. **Google (optional)** — `credentials.json` status, a button to start authorization
   (the flow from stage 4; the wizard shows the URL + a field for the code), sync toggles
9. **Summary** — review the settings, a final "say the phrase and add a note" test,
   `setup_completed=true`

Steps 5 and 6 must also work when there's no hardware ("Skip — I'll configure this
later"): missing hardware must never block using the site.

## Implementation tasks

1. `settings` table + API + validation (Pydantic settings models)
2. `POST /api/voice/test/{mic|speaker|button|led|wake}` endpoints — proxy to the voice
   service (communication: a small HTTP server in the voice service on localhost:8090,
   or a file-based queue — pick the simpler option and document it)
3. Wizard templates (mobile-first, big buttons, clear messages, Basecoat components throughout)
4. Audio device and RAM detection on the backend (system endpoints)
5. After saving settings: notify the voice service (SIGHUP via systemd, or a reload endpoint)
6. Tests: wizard flow with a mocked voice service; settings migration

## Acceptance criteria

- [ ] A fresh database → visiting the site → the wizard walks you from zero to a working
      assistant without touching a terminal (beyond what's described in docs/)
- [ ] Microphone, speaker, button, LED, and wake-phrase tests all work from the browser
- [ ] Changing the phrase/sensitivity in a re-run wizard works without a Pi restart
- [ ] "Skip" on the hardware steps → the site is fully usable (voice-free mode)
- [ ] `pytest -q` green
