"""
Alembic env — связка миграций с нашими SQLAlchemy-моделями.

≈ Laravel: миграции знают о схеме Eloquent-моделей.
Здесь target_metadata = Base.metadata → autogenerate видит TicketModel/NoteModel.

URL: postgresql+asyncpg://... из Settings (DATABASE_URL).
Миграции гоняем через async engine + run_sync (стандартный приём с async SQLAlchemy).
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from essentials_lab.config import get_settings

# Импорт моделей обязателен, иначе metadata будет пустой при autogenerate
from essentials_lab.db import models as _models  # noqa: F401
from essentials_lab.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Подставляем URL из .env / окружения (как config/database.php + .env)
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Генерация SQL без живого коннекта (редко нужно)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
