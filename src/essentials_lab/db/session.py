"""
Подключение к Postgres: async engine + фабрика сессий.

≈ Laravel DB connection + «одна транзакция на запрос».
AsyncSession нельзя использовать как sync Eloquent — везде await.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from essentials_lab.config import Settings
from essentials_lab.db.models import Base


def create_engine(settings: Settings) -> AsyncEngine:
    """
    Пул соединений к БД.

    pool_pre_ping=True — перед выдачей соединения проверить, что оно живо
    (полезно после idle timeout Postgres/Docker).
    """
    return create_async_engine(settings.database_url, echo=settings.debug, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Фабрика сессий (не сама сессия).

    expire_on_commit=False — после commit атрибуты объекта не «протухают»
    (удобно сразу читать id/поля без лишнего refresh).
    """
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine: AsyncEngine) -> None:
    """
    Создать таблицы, если их ещё нет (учебный упрощённый вариант миграций).

    В проде обычно Alembic (≈ Laravel migrations).
    run_sync нужен, потому что metadata.create_all — синхронный API.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """
    Контекстный помощник: commit при успехе, rollback при ошибке.

    В HTTP-слое похожая логика лежит в api/deps.get_db_session.
    """
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
