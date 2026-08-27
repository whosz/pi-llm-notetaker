import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import async_session as default_session_maker
from app.llm.client import OllamaError, classify
from app.llm.parser import parse_classification
from app.llm.prompts import build_system_prompt
from app.models import ListItem, Note

logger = logging.getLogger(__name__)

SHOPPING_MERGE_WINDOW = timedelta(hours=24)

_queue: asyncio.Queue[int] = asyncio.Queue()


async def enqueue(note_id: int) -> None:
    await _queue.put(note_id)


async def enqueue_pending(db: AsyncSession) -> None:
    ids = (
        (await db.execute(select(Note.id).where(Note.status == "pending")))
        .scalars()
        .all()
    )
    for note_id in ids:
        await enqueue(note_id)


async def _find_recent_shopping_note(db: AsyncSession, exclude_id: int) -> Note | None:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - SHOPPING_MERGE_WINDOW
    stmt = (
        select(Note)
        .where(
            Note.type == "shopping",
            Note.status == "processed",
            Note.id != exclude_id,
            Note.created_at >= cutoff,
        )
        .order_by(Note.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def process_note(
    note_id: int, session_maker: async_sessionmaker[AsyncSession] | None = None
) -> None:
    session_maker = session_maker or default_session_maker
    async with session_maker() as db:
        note = await db.get(Note, note_id)
        if note is None:
            return

        system_prompt = build_system_prompt()
        try:
            raw = await classify(system_prompt, note.raw_text)
        except OllamaError as e:
            note.status = "error"
            note.error_msg = str(e)
            await db.commit()
            logger.warning("Ollama unreachable for note %s: %s", note_id, e)
            return

        result = parse_classification(raw)
        if result is None:
            try:
                raw = await classify(
                    system_prompt
                    + f"\n\nYour previous response was not valid JSON: {raw!r}. Try again.",
                    note.raw_text,
                )
            except OllamaError as e:
                note.status = "error"
                note.error_msg = str(e)
                await db.commit()
                return
            result = parse_classification(raw)

        if result is None:
            # A note is never lost: fall back to a plain note rather than erroring out.
            note.type = "note"
            note.title = note.raw_text[:60]
            note.payload = {"confidence": 0.0}
            note.status = "processed"
            await db.commit()
            return

        note.type = result.type
        note.title = result.title or note.raw_text[:60]
        payload: dict = {"confidence": result.confidence}
        if result.type == "meeting" and result.datetime:
            payload["datetime"] = result.datetime
        if result.type == "task" and result.due:
            payload["due"] = result.due

        if result.type == "shopping" and result.items:
            target = await _find_recent_shopping_note(db, exclude_id=note.id)
            if target is not None:
                start = len(target.items)
                for i, text in enumerate(result.items):
                    db.add(ListItem(note_id=target.id, text=text, position=start + i))
                payload["merged_into_note_id"] = target.id
            else:
                for i, text in enumerate(result.items):
                    db.add(ListItem(note_id=note.id, text=text, position=i))

        note.payload = payload
        note.status = "processed"
        await db.commit()


async def worker_loop() -> None:
    while True:
        note_id = await _queue.get()
        try:
            await process_note(note_id)
        except Exception:
            logger.exception("Unhandled error processing note %s", note_id)
        finally:
            _queue.task_done()
