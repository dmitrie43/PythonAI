"""
Юнит-тесты без Docker: доменные правила и Pydantic-валидация.

pytest сам находит функции test_*.
pytest.raises — ожидание исключения (≈ expectException в PHPUnit).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from essentials_lab.domain import Ticket, TicketStatus
from essentials_lab.schemas import TicketCreate


def _ticket(status: TicketStatus) -> Ticket:
    """Мини-фабрика тестового тикета (без БД)."""
    now = datetime.now(UTC)
    return Ticket(
        id=1,
        title="Test",
        status=status,
        priority=3,
        created_at=now,
        updated_at=now,
    )


def test_cannot_add_note_when_resolved() -> None:
    """Resolved → ValueError (это потом станет HTTP 409 в API)."""
    ticket = _ticket(TicketStatus.RESOLVED)
    with pytest.raises(ValueError, match="resolved"):
        ticket.assert_can_add_note()


def test_can_add_note_when_open() -> None:
    """Open — правило молча пропускает."""
    _ticket(TicketStatus.OPEN).assert_can_add_note()


def test_ticket_create_schema_priority_bounds() -> None:
    """Pydantic Field(ge=1, le=5) и min_length=3 — как validation rules."""
    TicketCreate(title="Valid title", priority=1)
    with pytest.raises(ValidationError):
        TicketCreate(title="Valid title", priority=9)  # priority слишком большой
    with pytest.raises(ValidationError):
        TicketCreate(title="ab", priority=3)  # title слишком короткий
