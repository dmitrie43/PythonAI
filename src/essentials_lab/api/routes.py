"""
HTTP-роуты (≈ Laravel routes/api.php + Controller).

Здесь только:
  - принять/отвалидировать вход (Pydantic через type hints);
  - вызвать сервис;
  - перевести доменные ошибки в HTTP-коды.

Бизнес-логика — в services/domain, SQL — в repositories.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text

from essentials_lab.api.deps import get_ticket_service
from essentials_lab.domain import TicketStatus
from essentials_lab.schemas import (
    HealthOut,
    NoteCreate,
    NoteOut,
    TicketCreate,
    TicketOut,
    TicketStatusUpdate,
)
from essentials_lab.services import TicketNotFoundError, TicketService

# Все пути ниже монтируются с префиксом /api в main.create_app
router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def health(request: Request) -> HealthOut:
    """
    Liveness/readiness для Docker: живы ли Postgres и Redis.

    Не через TicketService — это инфраструктурная проверка.
    """
    db_ok = "ok"
    redis_ok = "ok"
    try:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = "error"
    try:
        await request.app.state.redis.ping()
    except Exception:
        redis_ok = "error"

    overall = "ok" if db_ok == "ok" and redis_ok == "ok" else "degraded"
    return HealthOut(status=overall, database=db_ok, redis=redis_ok)


@router.post("/tickets", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,  # JSON body → автоматически в модель; ошибка → 422
    service: TicketService = Depends(get_ticket_service),
) -> TicketOut:
    """POST /api/tickets — создать тикет."""
    return await service.create_ticket(title=payload.title, priority=payload.priority)


@router.get("/tickets", response_model=list[TicketOut])
async def list_tickets(
    # alias="status" → query ?status=open, имя аргумента в Python другое (status — занято)
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    service: TicketService = Depends(get_ticket_service),
) -> list[TicketOut]:
    """GET /api/tickets?status=open — список."""
    return await service.list_tickets(status=status_filter)


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
async def get_ticket(
    ticket_id: int,  # path-параметр /tickets/7
    service: TicketService = Depends(get_ticket_service),
) -> TicketOut:
    """GET /api/tickets/{id} — чтение (с Redis cache-aside внутри сервиса)."""
    try:
        return await service.get_ticket(ticket_id)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/tickets/{ticket_id}/status", response_model=TicketOut)
async def update_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    service: TicketService = Depends(get_ticket_service),
) -> TicketOut:
    """PATCH /api/tickets/{id}/status — смена статуса."""
    try:
        return await service.update_status(ticket_id, payload.status)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/tickets/{ticket_id}/notes",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_note(
    ticket_id: int,
    payload: NoteCreate,
    service: TicketService = Depends(get_ticket_service),
) -> NoteOut:
    """
    POST /api/tickets/{id}/notes

    404 — тикета нет
    409 — бизнес-конфликт (например, тикет resolved)
    """
    try:
        return await service.add_note(ticket_id, body=payload.body, author=payload.author)
    except TicketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
