import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import async_session, init_db
from app.llm.worker import enqueue_pending, worker_loop
from app.routers import notes, ui


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session() as db:
        await enqueue_pending(db)
    task = asyncio.create_task(worker_loop())
    yield
    task.cancel()


app = FastAPI(title="PiLLm Note Taker", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(notes.router)
app.include_router(ui.router)
