"""
Middleware FastAPI/Starlette (≈ Laravel Middleware / Kernel::$middleware).

Порядок в create_app важен: последний добавленный add_middleware
оборачивает снаружи первым (как матрёшка).

Цепочка для запроса:
  RequestId → RateLimit → роут → ... → ответ обратно через те же слои
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from essentials_lab.config import Settings


def _is_rate_limit_exempt(path: str) -> bool:
    """Health и документация не должны ловить 429."""
    if path == "/api/health":
        return True
    return path.startswith(("/docs", "/redoc", "/openapi.json"))


def _client_ip(request: Request) -> str:
    """
    IP клиента для ключа лимита.

    За прокси смотрим X-Forwarded-For (первый адрес в цепочке).
    В чистом Compose часто будет IP gateway Docker-сети.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Вешает X-Request-ID на каждый ответ (и кладёт в request.state).

    Зачем: связать логи «этот запрос» по всей цепочке retrieve→LLM позже.
    Клиент может прислать свой X-Request-ID — тогда переиспользуем.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Fixed-window rate limit в Redis (≈ Laravel RateLimiter / throttle).

    Алгоритм (просто для учёбы):
      ключ = rl:{ip}:{номер_окна}
      INCR; если первый раз — EXPIRE на window_seconds
      если count > limit → HTTP 429

    Окно фиксированное: в пределах window_seconds лимит общий, потом счётчик новый.
    (Sliding window сложнее; для пилота fixed обычно хватает.)
    """

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._settings.rate_limit_enabled:
            return await call_next(request)

        if _is_rate_limit_exempt(request.url.path):
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            # Redis ещё не готов (крайний случай до lifespan) — не блокируем
            return await call_next(request)

        limit = self._settings.rate_limit_requests
        window = self._settings.rate_limit_window_seconds
        ip = _client_ip(request)
        window_id = int(time.time()) // window
        key = f"rl:{ip}:{window_id}"

        try:
            count = int(await redis.incr(key))
            if count == 1:
                await redis.expire(key, window)
        except Exception:
            # Redis упал — fail-open: лучше обслужить, чем положить весь API
            return await call_next(request)

        remaining = max(0, limit - count)
        reset_at = (window_id + 1) * window

        if count > limit:
            retry_after = max(1, reset_at - int(time.time()))
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": limit,
                    "window_seconds": window,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response
