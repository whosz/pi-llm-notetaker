from datetime import datetime, timedelta

SYSTEM_PROMPT_TEMPLATE = """You classify short personal notes into a single structured JSON object. Respond with ONLY the JSON object, no other text, no markdown code fences.

Today is {today} ({weekday}). Resolve relative dates ("tomorrow", "on Friday") against this.

JSON shape:
{{"type": "shopping|meeting|task|quote|idea|note", "title": "short title", "items": [], "datetime": null, "due": null, "confidence": 0.0}}

- type: pick the single best fit
- items: only for "shopping" — list of individual items mentioned
- datetime: only for "meeting" — ISO 8601 date and time, or null
- due: only for "task" — ISO 8601 date, or null
- confidence: 0.0-1.0, how sure you are

Examples:

Note: "buy milk, bread and 2x butter"
{{"type": "shopping", "title": "Shopping list", "items": ["milk", "bread", "butter", "butter"], "datetime": null, "due": null, "confidence": 0.95}}

Note: "meeting with Anna tomorrow at 3pm about the project"
{{"type": "meeting", "title": "Meeting with Anna", "items": [], "datetime": "{tomorrow}T15:00:00", "due": null, "confidence": 0.9}}

Note: "call the dentist by Friday"
{{"type": "task", "title": "Call the dentist", "items": [], "datetime": null, "due": "{friday}", "confidence": 0.85}}
"""


def build_system_prompt(now: datetime | None = None) -> str:
    now = now or datetime.now()  # noqa: DTZ005 — intentionally local wall-clock date,
    # so "tomorrow"/"Friday" resolve against the user's own calendar day, not UTC
    tomorrow = (now + timedelta(days=1)).date().isoformat()
    days_until_friday = (4 - now.weekday()) % 7 or 7
    friday = (now + timedelta(days=days_until_friday)).date().isoformat()
    return SYSTEM_PROMPT_TEMPLATE.format(
        today=now.date().isoformat(),
        weekday=now.strftime("%A"),
        tomorrow=tomorrow,
        friday=friday,
    )
