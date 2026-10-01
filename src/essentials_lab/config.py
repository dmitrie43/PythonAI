"""
Конфигурация приложения из переменных окружения.

Аналог Laravel: файл .env + config/*.php.
Pydantic Settings сам читает DATABASE_URL → database_url и т.п.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Все настройки в одном типизированном объекте."""

    # extra="ignore" — неизвестные ключи в .env не роняют старт
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "py-essentials-lab"
    debug: bool = False  # True → SQL echo + uvicorn reload

    # postgresql+asyncpg://... — драйвер asyncpg обязателен для async SQLAlchemy
    database_url: str = "postgresql+asyncpg://essentials:essentials@localhost:5432/essentials"
    redis_url: str = "redis://localhost:6379/0"

    cache_ttl_seconds: int = 60  # TTL кэша тикета в Redis
    api_host: str = "0.0.0.0"  # слушать все интерфейсы (нужно в Docker)
    api_port: int = 8000

    # Rate limit (fixed window в Redis). Для локальных тестов можно поднять лимит.
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120  # макс. запросов с одного IP за окно
    rate_limit_window_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    """
    Один экземпляр Settings на процесс (как singleton config).

    lru_cache без аргументов = «вычислить один раз и запомнить».
    FastAPI Depends(get_settings) будет переиспользовать тот же объект.
    """
    return Settings()
