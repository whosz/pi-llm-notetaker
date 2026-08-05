from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_text: Mapped[str] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(String(20), default=None)
    title: Mapped[str | None] = mapped_column(String(200), default=None)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_msg: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["ListItem"]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
        order_by="ListItem.position",
        lazy="selectin",
    )


class ListItem(Base):
    __tablename__ = "list_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(500))
    checked: Mapped[bool] = mapped_column(default=False)
    position: Mapped[int] = mapped_column(default=0)

    note: Mapped["Note"] = relationship(back_populates="items")


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"))
    target: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str | None] = mapped_column(String(200), default=None)
    synced_at: Mapped[datetime] = mapped_column(server_default=func.now())
    status: Mapped[str] = mapped_column(String(20))
