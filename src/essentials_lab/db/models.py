"""
ORM-модели SQLAlchemy 2.x — явное описание таблиц.

≈ Eloquent Model, но маппинг колонок пишете сами (не «магия атрибутов»).
Важно: это НЕ доменный Ticket. Репозиторий конвертирует Model → domain.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from essentials_lab.domain import TicketStatus


class Base(DeclarativeBase):
    """Базовый класс всех таблиц. metadata.create_all() берёт схемы отсюда."""

    pass


class TicketModel(Base):
    """Таблица tickets."""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # status храним строкой; enum — в домене. Индекс ускоряет фильтр ?status=
    status: Mapped[str] = mapped_column(String(32), default=TicketStatus.OPEN.value, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    # server_default=func.now() — значение ставит Postgres, не Python
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationship ≈ hasMany(Note::class)
    # cascade: удалили тикет → удалились заметки
    notes: Mapped[list[NoteModel]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="NoteModel.id",
    )


class NoteModel(Base):
    """Таблица notes (belongsTo ticket)."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # ON DELETE CASCADE на уровне FK в Postgres
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped[TicketModel] = relationship(back_populates="notes")
