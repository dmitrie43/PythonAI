"""
Запуск Alembic из кода приложения (startup / CLI).

≈ Artisan::call('migrate') при деплое или в контейнере.

Важно: command.upgrade внутри поднимает свой event loop (см. alembic/env.py).
Поэтому из async lifespan вызывайте через asyncio.to_thread(run_migrations, ...).
"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command
from essentials_lab.config import Settings, get_settings


def _find_alembic_ini() -> Path:
    """Ищем alembic.ini в cwd, /app (Docker) или выше по дереву от этого файла."""
    candidates = [Path.cwd() / "alembic.ini", Path("/app/alembic.ini")]
    for parent in Path(__file__).resolve().parents:
        candidates.append(parent / "alembic.ini")
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "alembic.ini not found. Run from repo root or ensure it is copied into the image."
    )


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(_find_alembic_ini()))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def run_migrations(settings: Settings | None = None) -> None:
    """Накатить все миграции до head (alembic upgrade head)."""
    settings = settings or get_settings()
    command.upgrade(_alembic_config(settings.database_url), "head")


def main() -> None:
    """CLI: essentials-migrate  (≈ php artisan migrate)."""
    run_migrations()
    print("Migrations applied (alembic upgrade head).")


if __name__ == "__main__":
    main()
