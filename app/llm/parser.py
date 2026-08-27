import json
import re

from pydantic import ValidationError

from app.schemas import LLMClassification


def parse_classification(raw: str) -> LLMClassification | None:
    """Defensively parse an LLM response into a validated classification.

    Strips stray text/code fences around the JSON object, then validates the
    shape. Returns None (never raises) if the response isn't usable — callers
    decide whether to retry or fall back.
    """
    match = re.search(r"\{.*\}", raw.strip(), re.DOTALL)
    candidate = match.group(0) if match else raw
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    try:
        return LLMClassification.model_validate(data)
    except ValidationError:
        return None
