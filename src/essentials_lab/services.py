"""
Application Service — сценарии use-case.

≈ Laravel Action / Application Service:
  - вызывает repository + cache;
  - применяет доменные правила;
  - отдаёт Pydantic DTO наружу (готовые к JSON).

HTTP-слой не должен сам решать, ходить ли в Redis.
"""

from __future__ import annotations

from essentials_lab.cache import TicketCache
from essentials_lab.domain import Ticket, TicketStatus
from essentials_lab.repositories import TicketRepository
from essentials_lab.schemas import NoteOut, TicketOut


class TicketNotFoundError(LookupError):
    """Доменное «не найдено». Роут превратит в HTTP 404."""

    pass


class TicketService:
    def __init__(self, repo: TicketRepository, cache: TicketCache) -> None:
        self._repo = repo
        self._cache = cache

    async def create_ticket(self, *, title: str, priority: int) -> TicketOut:
        ticket = await self._repo.create(title=title, priority=priority)
        return self._to_out(ticket)

    async def list_tickets(self, *, status: TicketStatus | None = None) -> list[TicketOut]:
        tickets = await self._repo.list(status=status)
        return [self._to_out(t) for t in tickets]

    async def get_ticket(self, ticket_id: int) -> TicketOut:
        """
        Cache-aside:
          1) Redis hit  → сразу ответ (cached=True)
          2) Redis miss → Postgres → положить в Redis → ответ
        """
        cached = await self._cache.get(ticket_id)
        if cached is not None:
            # **cached распаковывает dict в поля TicketOut
            return TicketOut(**cached, cached=True)

        ticket = await self._repo.get(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")

        out = self._to_out(ticket)
        # mode="json" — datetime уже в ISO-строки, удобно класть в Redis
        await self._cache.set(ticket_id, out.model_dump(mode="json", exclude={"cached"}))
        return out

    async def update_status(self, ticket_id: int, status: TicketStatus) -> TicketOut:
        ticket = await self._repo.update_status(ticket_id, status)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")
        await self._cache.invalidate(ticket_id)  # данные изменились
        return self._to_out(ticket)

    async def add_note(self, ticket_id: int, *, body: str, author: str) -> NoteOut:
        existing = await self._repo.get(ticket_id)
        if existing is None:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")
        # Правило домена: в resolved нельзя писать → ValueError → HTTP 409 в routes
        existing.assert_can_add_note()

        note = await self._repo.add_note(ticket_id, body=body, author=author)
        if note is None:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")
        await self._cache.invalidate(ticket_id)
        return NoteOut(
            id=note.id,
            ticket_id=note.ticket_id,
            body=note.body,
            author=note.author,
            created_at=note.created_at,
        )

    @staticmethod
    def _to_out(ticket: Ticket, *, cached: bool = False) -> TicketOut:
        """domain.Ticket → схемa ответа API."""
        return TicketOut(
            id=ticket.id,
            title=ticket.title,
            status=ticket.status,
            priority=ticket.priority,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            notes=[
                NoteOut(
                    id=n.id,
                    ticket_id=n.ticket_id,
                    body=n.body,
                    author=n.author,
                    created_at=n.created_at,
                )
                for n in ticket.notes
            ],
            cached=cached,
        )
