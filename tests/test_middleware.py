"""Юнит-тесты middleware без Docker."""

from __future__ import annotations

from essentials_lab.api.middleware import _is_rate_limit_exempt


def test_health_is_exempt() -> None:
    assert _is_rate_limit_exempt("/api/health") is True


def test_tickets_not_exempt() -> None:
    assert _is_rate_limit_exempt("/api/tickets") is False
    assert _is_rate_limit_exempt("/api/tickets/1") is False


def test_docs_exempt() -> None:
    assert _is_rate_limit_exempt("/docs") is True
    assert _is_rate_limit_exempt("/docs/oauth2-redirect") is True
    assert _is_rate_limit_exempt("/openapi.json") is True
