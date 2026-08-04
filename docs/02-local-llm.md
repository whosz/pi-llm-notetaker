# 02 — Local LLM on the Pi 4 (Ollama)

Goal: a working local language model with an HTTP API on `localhost:11434`,
capable of classifying and structuring notes.

## Why Ollama

- Official ARM64 / Raspberry Pi support
- Simple HTTP API (the backend talks to it with a single POST)
- Easy to download and swap models
- Handles quantization and memory management itself

📚 Official site: <https://ollama.com> · [API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)

## Installation

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

The installer creates a systemd service (`ollama.service`) on its own, so Ollama starts with the system.
Check:

```bash
systemctl status ollama
curl http://localhost:11434/api/tags   # should return JSON with a list of models (empty for now)
```

## Choosing a model

Only small models are realistic on a Pi 4. Our task (note classification + field
extraction into JSON) doesn't need a large model — speed matters more.

| Model | Size | RAM in use | Pi 4 GB | Pi 8 GB | Notes |
|---|---|---|---|---|---|
| `qwen2.5:0.5b` | ~0.4 GB | ~1 GB | ✅ | ✅ | Very fast, surprisingly good at JSON |
| `qwen2.5:1.5b` | ~1 GB | ~2 GB | ✅ | ✅ | **Recommended starting point** — good balance |
| `llama3.2:1b` | ~1.3 GB | ~2 GB | ✅ | ✅ | Alternative |
| `llama3.2:3b` | ~2 GB | ~3.5 GB | ⚠️ tight | ✅ | Better quality, slower (~2–4 tok/s) |
| `gemma2:2b` | ~1.6 GB | ~3 GB | ⚠️ | ✅ | Good alternative |

> The **Qwen2.5** family performs exceptionally well on the Pi for "return JSON"
> tasks, which is why it's the project's default choice.

Download and test:

```bash
ollama pull qwen2.5:1.5b
ollama run qwen2.5:1.5b "Classify this note: 'buy milk, bread and butter'. Answer with one word: shopping/quote/meeting/other"
```

## API test (this is how the backend will use it)

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:1.5b",
  "stream": false,
  "format": "json",
  "messages": [
    {"role": "system", "content": "You classify notes. Respond with ONLY valid JSON: {\"type\": \"shopping|quote|meeting|task|note\", \"title\": \"...\", \"items\": []}"},
    {"role": "user", "content": "meeting with Anna on Friday at 3pm about the project"}
  ]
}'
```

Note the `"format": "json"` — this forces Ollama to produce valid JSON output.
This greatly simplifies parsing on the backend.

📚 Good introduction: [Ollama — Structured outputs (blog)](https://ollama.com/blog/structured-outputs)

## Tuning for the Pi

In `/etc/systemd/system/ollama.service.d/override.conf` (create it via
`sudo systemctl edit ollama`) it's worth setting:

```ini
[Service]
Environment="OLLAMA_KEEP_ALIVE=30m"    # keep the model in RAM between requests
Environment="OLLAMA_NUM_PARALLEL=1"    # one request at a time (there's no headroom for more anyway)
Environment="OLLAMA_MAX_LOADED_MODELS=1"
```

Then: `sudo systemctl daemon-reload && sudo systemctl restart ollama`.

`OLLAMA_KEEP_ALIVE` is crucial — without it the model gets unloaded after 5 minutes
and the first request after a break waits tens of seconds for it to reload.

## Expected performance (so there are no surprises)

- Pi 4, `qwen2.5:1.5b`: ~4–8 tokens/s → classifying a note: **a few to a dozen seconds**
- That's why the app processes notes **in the background** (status `pending` → `processed`),
  not during the HTTP request — this is an assumption baked into the whole architecture (see `CLAUDE.md`).

## Voice control

The voice assistant (wake phrase, button, LED, STT/TTS) is an integral part of the
project — full hardware and audio stack description: [06-voice-and-hardware.md](06-voice-and-hardware.md).
With 4 GB RAM, keep in mind that the audio models (Vosk + Piper + wake word, ~200–300 MB)
live in RAM alongside the LLM — in that case pick `qwen2.5:0.5b` or `1.5b`.

## Checklist

- [ ] `curl http://localhost:11434/api/tags` returns the model in the list
- [ ] A classification test with `"format": "json"` returns sensible JSON
- [ ] `OLLAMA_KEEP_ALIVE` is set
- [ ] CPU temperature under load < 80°C

Next: [03-architecture.md](03-architecture.md)
