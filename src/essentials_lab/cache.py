"""
Кэш чтения тикета в Redis.

≈ Laravel Cache::remember / Cache::forget.
Храним JSON ответа (dict), не ORM-объекты — проще и безопаснее между процессами.
"""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis


class TicketCache:
    def __init__(self, redis: Redis, *, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    def _key(self, ticket_id: int) -> str:
        """Единый формат ключа: ticket:42."""
        return f"ticket:{ticket_id}"

    async def get(self, ticket_id: int) -> dict[str, Any] | None:
        """None = cache miss."""
        raw = await self._redis.get(self._key(ticket_id))
        if raw is None:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None

    async def set(self, ticket_id: int, payload: dict[str, Any]) -> None:
        """
        ex=TTL — ключ сам умрёт через N секунд.

        default=str в dumps — datetime → строка (иначе TypeError).
        """
        await self._redis.set(self._key(ticket_id), json.dumps(payload, default=str), ex=self._ttl)

    async def invalidate(self, ticket_id: int) -> None:
        """После изменения тикета/заметок кэш надо сбросить (иначе stale data)."""
        await self._redis.delete(self._key(ticket_id))
