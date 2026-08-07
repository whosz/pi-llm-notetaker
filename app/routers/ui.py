from typing import Annotated

from fastapi import APIRouter, Form, Request, Response

from app.db import DbSession
from app.models import ListItem, Note
from app.routers.notes import build_notes_stmt, get_note_or_404
from app.templating import templates

router = APIRouter()

DEFAULT_LIMIT = 20


@router.get("/")
async def index(
    request: Request, db: DbSession, type: str | None = None, q: str | None = None
) -> Response:
    result = await db.execute(build_notes_stmt(type, q, DEFAULT_LIMIT, 0))
    notes = list(result.scalars().all())
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "notes": notes,
            "type": type,
            "active_type": type,
            "q": q,
            "limit": DEFAULT_LIMIT,
            "offset": 0,
        },
    )


@router.get("/notes-list")
async def notes_list(
    request: Request,
    db: DbSession,
    type: str | None = None,
    q: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> Response:
    result = await db.execute(build_notes_stmt(type, q, limit, offset))
    notes = list(result.scalars().all())
    return templates.TemplateResponse(
        request,
        "partials/notes_list.html",
        {"notes": notes, "type": type, "q": q, "limit": limit, "offset": offset},
    )


@router.post("/notes")
async def create_note(
    request: Request, db: DbSession, text: Annotated[str, Form()]
) -> Response:
    note = Note(raw_text=text)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return templates.TemplateResponse(
        request, "partials/note_card.html", {"note": note}
    )


@router.get("/notes/{note_id}/card")
async def note_card(request: Request, note_id: int, db: DbSession) -> Response:
    note = await get_note_or_404(note_id, db)
    return templates.TemplateResponse(
        request, "partials/note_card.html", {"note": note}
    )


@router.patch("/notes/{note_id}")
async def update_note(
    request: Request,
    note_id: int,
    db: DbSession,
    raw_text: Annotated[str, Form()],
    type: Annotated[str, Form()] = "",
) -> Response:
    note = await get_note_or_404(note_id, db)
    note.raw_text = raw_text
    note.type = type or None
    await db.commit()
    await db.refresh(note)
    return templates.TemplateResponse(
        request, "partials/note_card.html", {"note": note}
    )


@router.delete("/notes/{note_id}")
async def delete_note(note_id: int, db: DbSession) -> Response:
    note = await get_note_or_404(note_id, db)
    await db.delete(note)
    await db.commit()
    return Response(content="", media_type="text/html")


@router.post("/notes/{note_id}/retry")
async def retry_note(request: Request, note_id: int, db: DbSession) -> Response:
    note = await get_note_or_404(note_id, db)
    note.status = "pending"
    note.error_msg = None
    await db.commit()
    await db.refresh(note)
    return templates.TemplateResponse(
        request, "partials/note_card.html", {"note": note}
    )


@router.post("/items/{item_id}/toggle")
async def toggle_item(request: Request, item_id: int, db: DbSession) -> Response:
    item = await db.get(ListItem, item_id)
    if item is None:
        return Response(content="", status_code=404)
    item.checked = not item.checked
    await db.commit()
    await db.refresh(item)
    return templates.TemplateResponse(
        request, "partials/list_item.html", {"item": item}
    )
