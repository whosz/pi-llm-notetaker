from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import DbSession
from app.llm.worker import enqueue
from app.models import ListItem, Note
from app.schemas import ListItemOut, ListItemUpdate, NoteCreate, NoteOut, NoteUpdate

router = APIRouter(prefix="/api", tags=["notes"])


def build_notes_stmt(
    type: str | None = None, q: str | None = None, limit: int = 20, offset: int = 0
) -> Select:
    stmt = select(Note).order_by(Note.created_at.desc()).limit(limit).offset(offset)
    if type:
        stmt = stmt.where(Note.type == type)
    if q:
        stmt = stmt.where(Note.raw_text.icontains(q))
    return stmt


async def get_note_or_404(note_id: int, db: AsyncSession) -> Note:
    note = await db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/notes", response_model=NoteOut, status_code=202)
async def create_note(payload: NoteCreate, db: DbSession) -> Note:
    note = Note(raw_text=payload.text)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    await enqueue(note.id)
    return note


@router.get("/notes", response_model=list[NoteOut])
async def list_notes(
    db: DbSession,
    type: str | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Note]:
    result = await db.execute(build_notes_stmt(type, q, limit, offset))
    return list(result.scalars().all())


@router.get("/notes/{note_id}", response_model=NoteOut)
async def get_note(note_id: int, db: DbSession) -> Note:
    return await get_note_or_404(note_id, db)


@router.patch("/notes/{note_id}", response_model=NoteOut)
async def update_note(note_id: int, payload: NoteUpdate, db: DbSession) -> Note:
    note = await get_note_or_404(note_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: int, db: DbSession) -> Response:
    note = await get_note_or_404(note_id, db)
    await db.delete(note)
    await db.commit()
    return Response(status_code=204)


@router.patch("/items/{item_id}", response_model=ListItemOut)
async def update_item(item_id: int, payload: ListItemUpdate, db: DbSession) -> ListItem:
    item = await db.get(ListItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    item.checked = payload.checked
    await db.commit()
    await db.refresh(item)
    return item
