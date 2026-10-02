"""
Подключение к Postgres: async engine + фабрика сессий.

≈ Laravel DB connection + «одна транзакция на запрос».
AsyncSession нельзя использовать как sync Eloquent — везде await.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from essentials_lab.config import Settings, get_settings
from essentials_lab.db.migrate import run_migrations


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


async def init_db(settings: Settings | None = None) -> None:
    """
    Накатить Alembic-миграции (≈ php artisan migrate).

    Раньше здесь был metadata.create_all(); теперь схема в alembic/versions/.
    to_thread — потому что Alembic env.py сам вызывает asyncio.run.
    """
    await asyncio.to_thread(run_migrations, settings or get_settings())


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
