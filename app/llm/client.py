import httpx

from app.config import get_settings


class OllamaError(Exception):
    """Ollama is unreachable or errored, even after retrying."""


async def classify(system_prompt: str, note_text: str) -> str:
    settings = get_settings()
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": note_text},
        ],
    }
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=120.0) as client:
        for _ in range(2):
            try:
                resp = await client.post(
                    f"{settings.ollama_url}/api/chat", json=payload
                )
                resp.raise_for_status()
                return resp.json()["message"]["content"]
            except httpx.HTTPError as e:
                last_error = e
    raise OllamaError(str(last_error))
