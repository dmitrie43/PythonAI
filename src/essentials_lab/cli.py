"""
CLI для наполнения БД демо-тикетами.

≈ php artisan db:seed
Запуск: essentials-seed -n 5  (внутри Docker: docker compose exec api essentials-seed -n 5)

asyncio.run(...) — мост из синхронного main() в async seed().
Без FastAPI: сами создаём engine/session, коммитим, закрываем.
"""

from __future__ import annotations

import argparse
import asyncio

from essentials_lab.config import get_settings
from essentials_lab.db.session import create_engine, create_session_factory, init_db
from essentials_lab.domain import TicketStatus
from essentials_lab.repositories import TicketRepository


async def seed(*, count: int) -> None:
    """Создать count тикетов с заметкой; чётные — сразу in_progress."""
    settings = get_settings()
    engine = create_engine(settings)
    await init_db(engine)
    factory = create_session_factory(engine)

    async with factory() as session:
        repo = TicketRepository(session)
        for i in range(1, count + 1):
            ticket = await repo.create(
                title=f"Sample ticket #{i}: VPN / onboarding question",
                priority=(i % 5) + 1,
            )
            await repo.add_note(
                ticket.id,
                body="Initial triage note from seed CLI.",
                author="seed-bot",
            )
            if i % 2 == 0:
                await repo.update_status(ticket.id, TicketStatus.IN_PROGRESS)
        await session.commit()

    await engine.dispose()
    print(f"Seeded {count} tickets into {settings.database_url}")


def build_parser() -> argparse.ArgumentParser:
    """Разбор argv (как Symfony Console / artisan options)."""
    parser = argparse.ArgumentParser(description="Seed sample tickets into PostgreSQL")
    parser.add_argument("-n", "--count", type=int, default=5, help="How many tickets to create")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    asyncio.run(seed(count=args.count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
