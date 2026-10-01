"""
FastAPI Dependencies — «проводка» зависимостей на каждый запрос.

≈ Laravel Service Container + method injection в Controller:
  function store(TicketService $service)

Depends(get_X) говорит фреймворку: перед хендлером вызови get_X и передай результат.
Цепочка: get_ticket_service → get_db_session + get_cache → get_redis + get_settings.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from essentials_lab.cache import TicketCache
from essentials_lab.config import Settings, get_settings
from essentials_lab.repositories import TicketRepository
from essentials_lab.services import TicketService


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """
    Одна AsyncSession на HTTP-запрос.

    yield — FastAPI открывает сессию до хендлера и закрывает после.
    Успех → commit; исключение → rollback (как DB::transaction в Laravel).
    request.app.state.* заполняется в main.lifespan при старте приложения.
    """
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_redis(request: Request) -> Redis:
    """Общий Redis-клиент из lifespan (не создавать новый на каждый запрос)."""
    return request.app.state.redis


def get_cache(
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> TicketCache:
    """Обёртка кэша с TTL из Settings."""
    return TicketCache(redis, ttl_seconds=settings.cache_ttl_seconds)


def get_ticket_service(
    session: AsyncSession = Depends(get_db_session),
    cache: TicketCache = Depends(get_cache),
) -> TicketService:
    """Собираем сервис из repo(session) + cache — готово к инъекции в роут."""
    return TicketService(TicketRepository(session), cache)
