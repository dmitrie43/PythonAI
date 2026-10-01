"""
Pydantic-схемы HTTP: валидация входа и формат ответа.

≈ Laravel Form Request (вход) + API Resource / JsonResource (выход).
FastAPI сам:
  - парсит JSON тела в TicketCreate;
  - отдаёт 422 при ошибке валидации;
  - сериализует TicketOut в JSON по response_model.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from essentials_lab.domain import TicketStatus


class NoteCreate(BaseModel):
    """Тело POST /tickets/{id}/notes."""

    body: str = Field(min_length=1, max_length=4000)
    author: str = Field(min_length=1, max_length=100)


class NoteOut(BaseModel):
    """Заметка в ответе API."""

    # from_attributes=True — можно собрать из объекта с атрибутами (ORM/dataclass)
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    body: str
    author: str
    created_at: datetime


class TicketCreate(BaseModel):
    """Тело POST /tickets. priority: 1..5 (как ge/le в validation rules)."""

    title: str = Field(min_length=3, max_length=200)
    priority: int = Field(default=3, ge=1, le=5)


class TicketStatusUpdate(BaseModel):
    """Тело PATCH /tickets/{id}/status."""

    status: TicketStatus  # только значения enum, иначе 422


class TicketOut(BaseModel):
    """
    Тикет в ответе API.

    cached=True означает «отдали из Redis», не из Postgres —
    удобно видеть работу кэша при обучении (обычно в проде так не светят).
    """

    id: int
    title: str
    status: TicketStatus
    priority: int
    created_at: datetime
    updated_at: datetime
    notes: list[NoteOut] = Field(default_factory=list)
    cached: bool = False


class HealthOut(BaseModel):
    """Ответ /api/health для Docker/k8s probes."""

    status: str
    database: str
    redis: str
