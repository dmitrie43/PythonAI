"""
Репозиторий тикетов: только работа с БД, без HTTP и без Redis.

≈ Repository / Query Builder слой.
Наружу всегда отдаём domain.Ticket / domain.Note, не TicketModel.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from essentials_lab.db.models import NoteModel, TicketModel
from essentials_lab.domain import Note, Ticket, TicketStatus


class TicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        # Сессия приходит «снаружи» (DI) — один запрос HTTP ≈ одна сессия
        self._session = session

    async def create(self, *, title: str, priority: int) -> Ticket:
        """Вставить тикет. flush даёт id до commit."""
        row = TicketModel(title=title, priority=priority, status=TicketStatus.OPEN.value)
        self._session.add(row)
        await self._session.flush()  # INSERT, получить id (транзакция ещё открыта)
        await self._session.refresh(row)  # подтянуть server_default (created_at и т.д.)
        # В async нельзя лениво трогать row.notes → MissingGreenlet.
        # У нового тикета заметок нет — передаём пустой список явно.
        return self._to_domain(row, notes_override=[])

    async def get(self, ticket_id: int) -> Ticket | None:
        """
        Тикет + заметки одним запросом.

        selectinload — отдельный SELECT notes WHERE ticket_id IN (...)
        (eager load, безопасный для async; lazy load в async — ловушка).
        """
        row = await self._session.scalar(
            select(TicketModel)
            .where(TicketModel.id == ticket_id)
            .options(selectinload(TicketModel.notes))
        )
        return self._to_domain(row) if row else None

    async def list(self, *, status: TicketStatus | None = None, limit: int = 50) -> list[Ticket]:
        """Список с опциональным фильтром по статусу."""
        stmt = (
            select(TicketModel)
            .options(selectinload(TicketModel.notes))
            .order_by(TicketModel.id.desc())
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(TicketModel.status == status.value)
        rows = (await self._session.scalars(stmt)).all()
        return [self._to_domain(r) for r in rows]

    async def update_status(self, ticket_id: int, status: TicketStatus) -> Ticket | None:
        """Сменить статус и вернуть актуальный агрегат (с notes)."""
        row = await self._session.get(TicketModel, ticket_id)
        if row is None:
            return None
        row.status = status.value
        await self._session.flush()
        return await self.get(ticket_id)

    async def add_note(self, ticket_id: int, *, body: str, author: str) -> Note | None:
        """Добавить заметку. Проверка «resolved?» — в сервисе/домене, не здесь."""
        ticket = await self._session.get(TicketModel, ticket_id)
        if ticket is None:
            return None
        note = NoteModel(ticket_id=ticket_id, body=body, author=author)
        self._session.add(note)
        await self._session.flush()
        await self._session.refresh(note)
        return Note(
            id=note.id,
            ticket_id=note.ticket_id,
            body=note.body,
            author=note.author,
            created_at=note.created_at,
        )

    @staticmethod
    def _to_domain(
        row: TicketModel,
        *,
        notes_override: list[Note] | None = None,
    ) -> Ticket:
        """ORM → доменная модель (антикоррупционный слой в миниатюре)."""
        if notes_override is not None:
            notes = notes_override
        else:
            notes = [
                Note(
                    id=n.id,
                    ticket_id=n.ticket_id,
                    body=n.body,
                    author=n.author,
                    created_at=n.created_at,
                )
                for n in (row.notes or [])
            ]
        return Ticket(
            id=row.id,
            title=row.title,
            status=TicketStatus(row.status),
            priority=row.priority,
            created_at=row.created_at,
            updated_at=row.updated_at,
            notes=notes,
        )
