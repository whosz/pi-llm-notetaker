from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

NoteType = Literal["shopping", "meeting", "task", "quote", "idea", "note"]


class NoteCreate(BaseModel):
    text: str


class NoteUpdate(BaseModel):
    raw_text: str | None = None
    title: str | None = None
    type: NoteType | None = None


class ListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    checked: bool
    position: int


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_text: str
    type: str | None
    title: str | None
    payload: dict[str, Any]
    status: str
    error_msg: str | None
    created_at: datetime
    updated_at: datetime
    items: list[ListItemOut] = []


class ListItemUpdate(BaseModel):
    checked: bool


class LLMClassification(BaseModel):
    """Parsed, validated shape of the LLM's classification response."""

    type: NoteType = "note"
    title: str = ""
    items: list[str] = []
    datetime: str | None = None
    due: str | None = None
    confidence: float = 0.0
