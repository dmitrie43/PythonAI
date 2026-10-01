"""
Точка входа FastAPI-приложения.

uvicorn essentials_lab.main:app  — импортирует объект app ниже.
lifespan ≈ Laravel AppServiceProvider boot + shutdown:
  на старте открываем DB/Redis и создаём таблицы,
  на остановке закрываем соединения.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from redis.asyncio import Redis

from essentials_lab.api.middleware import RateLimitMiddleware, RequestIdMiddleware
from essentials_lab.api.routes import router
from essentials_lab.config import Settings, get_settings
from essentials_lab.db.session import create_engine, create_session_factory, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Код до yield — startup; после yield — shutdown.

    Всё важное кладём в app.state, чтобы deps/routes доставали без глобалов.
    """
    settings: Settings = app.state.settings
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    # decode_responses=True → Redis отдаёт str, не bytes
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    await init_db(engine)  # create tables if missing
    try:
        yield  # приложение работает, принимает запросы
    finally:
        await app.state.redis.aclose()
        await engine.dispose()  # закрыть пул соединений


def create_app(settings: Settings | None = None) -> FastAPI:
    """Фабрика приложения (удобно в тестах подставлять другие Settings)."""
    settings = settings or get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.settings = settings
    app.include_router(router, prefix="/api")  # /health → /api/health

    # Middleware: последний add_* выполняется «снаружи» первым.
    # Итог: RequestId → RateLimit → роуты.
    app.add_middleware(RateLimitMiddleware, settings=settings)
    app.add_middleware(RequestIdMiddleware)
    return app


# Объект, который подхватывает uvicorn / Docker CMD
app = create_app()


def run() -> None:
    """Консольная команда essentials-api (см. [project.scripts] в pyproject.toml)."""
    settings = get_settings()
    uvicorn.run(
        "essentials_lab.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    # python -m essentials_lab.main
    run()
