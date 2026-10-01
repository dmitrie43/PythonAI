"""
Интеграционные тесты против живого Docker Compose (api + db + redis).

Запуск:
  docker compose up --build -d
  uv run pytest tests/test_api_integration.py

Если стек не поднят — тесты skip (не fail), чтобы `pytest` локально не краснел.

trust_env=False — httpx не берёт системный HTTP_PROXY (на Windows иначе
localhost часто уходит в прокси и ломается).
"""

from __future__ import annotations

import os

import httpx
import pytest

BASE_URL = os.getenv("ESSENTIALS_BASE_URL", "http://127.0.0.1:8000")

# Все тесты в файле — async; pytest-asyncio (asyncio_mode=auto в pyproject)
pytestmark = pytest.mark.asyncio


async def _api_up() -> bool:
    """Пинг /api/health: готов ли compose-стек."""
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=2.0, trust_env=False) as client:
            r = await client.get("/api/health")
            return r.status_code == 200 and r.json().get("status") == "ok"
    except Exception:
        return False


@pytest.fixture
async def require_stack() -> None:
    """Фикстура-предохранитель: нет стека → skip."""
    if not await _api_up():
        pytest.skip(
            "Stack not running. Start with: docker compose up --build -d "
            "(then wait for /api/health)"
        )


async def test_health(require_stack: None) -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0, trust_env=False) as client:
        r = await client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body["database"] == "ok"
        assert body["redis"] == "ok"


async def test_middleware_headers(require_stack: None) -> None:
    """Request-ID всегда; RateLimit-заголовки на API (не на health)."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0, trust_env=False) as client:
        health = await client.get("/api/health")
        assert health.status_code == 200
        assert "X-Request-ID" in health.headers
        # health exempt от rate limit — счётчик не трогаем, заголовков лимита нет
        assert "X-RateLimit-Limit" not in health.headers

        custom_id = "lab-test-request-id"
        tickets = await client.get("/api/tickets", headers={"X-Request-ID": custom_id})
        assert tickets.status_code == 200
        assert tickets.headers["X-Request-ID"] == custom_id
        assert tickets.headers["X-RateLimit-Limit"] == "120"
        assert "X-RateLimit-Remaining" in tickets.headers


async def test_ticket_flow_and_cache(require_stack: None) -> None:
    """
    Сквозной сценарий:
      create → get (miss) → get (hit) → note → invalidate → resolve → 409 на note
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0, trust_env=False) as client:
        created = await client.post(
            "/api/tickets",
            json={"title": "Cannot connect to VPN", "priority": 2},
        )
        assert created.status_code == 201
        ticket_id = created.json()["id"]

        # Первый GET — из Postgres, cached=false
        first = await client.get(f"/api/tickets/{ticket_id}")
        assert first.status_code == 200
        assert first.json()["cached"] is False

        # Второй GET — из Redis, cached=true
        second = await client.get(f"/api/tickets/{ticket_id}")
        assert second.status_code == 200
        assert second.json()["cached"] is True

        note = await client.post(
            f"/api/tickets/{ticket_id}/notes",
            json={"body": "Tried reset MFA", "author": "support"},
        )
        assert note.status_code == 201

        # После мутации кэш сброшен
        after_note = await client.get(f"/api/tickets/{ticket_id}")
        assert after_note.json()["cached"] is False
        assert len(after_note.json()["notes"]) >= 1

        resolved = await client.patch(
            f"/api/tickets/{ticket_id}/status",
            json={"status": "resolved"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "resolved"

        # Доменное правило → HTTP 409 Conflict
        blocked = await client.post(
            f"/api/tickets/{ticket_id}/notes",
            json={"body": "should fail", "author": "support"},
        )
        assert blocked.status_code == 409
