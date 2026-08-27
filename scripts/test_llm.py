"""Manual test against a live Ollama instance: prints the classified JSON + timing.

Usage: uv run python scripts/test_llm.py "buy milk and bread"
"""

import asyncio
import sys
import time

from app.llm.client import classify
from app.llm.parser import parse_classification
from app.llm.prompts import build_system_prompt


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/test_llm.py <note text>")
        raise SystemExit(1)
    text = " ".join(sys.argv[1:])

    prompt = build_system_prompt()
    start = time.monotonic()
    raw = await classify(prompt, text)
    elapsed = time.monotonic() - start

    print(f"raw response ({elapsed:.1f}s): {raw}")
    print(f"parsed: {parse_classification(raw)}")


if __name__ == "__main__":
    asyncio.run(main())
