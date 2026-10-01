"""
Доменный слой: сущности и правила без SQLAlchemy и без FastAPI.

Зачем отделять от ORM:
  - Ticket (здесь) — то, о чём думает бизнес;
  - TicketModel (db/models) — как строка лежит в Postgres.
Аналог: PHP DTO / Value Object vs Eloquent Model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class TicketStatus(StrEnum):
    """
    StrEnum → значение в БД/JSON = строка ("open"), а в коде — enum.
    В PHP 8.1+ похоже на backed enum: case Open = 'open'.
    """

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


@dataclass(slots=True)
class Note:
    """Заметка к тикету. slots=True — чуть меньше памяти, без произвольных атрибутов."""

    id: int
    ticket_id: int
    body: str
    author: str
    created_at: datetime


@dataclass(slots=True)
class Ticket:
    """Тикет поддержки + вложенные заметки."""

    id: int
    title: str
    status: TicketStatus
    priority: int
    created_at: datetime
    updated_at: datetime
    # default_factory=list — НЕ писать notes: list = [] (общий mutable default!)
    notes: list[Note] = field(default_factory=list)

    def assert_can_add_note(self) -> None:
        """
        Бизнес-правило живёт в домене, не в роуте.

        Роут только ловит ValueError и отдаёт HTTP 409.
        Так же в Laravel правило лучше держать в модели/Action, а не только в Controller.
        """
        if self.status == TicketStatus.RESOLVED:
            raise ValueError("Cannot add notes to a resolved ticket")
