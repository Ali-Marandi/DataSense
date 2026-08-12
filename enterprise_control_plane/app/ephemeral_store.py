"""Short-lived security state; Redis adapter is mandatory in production."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol


class EphemeralStore(Protocol):
    async def put(self, namespace: str, key: str, value: dict[str, Any], ttl_seconds: int) -> None: ...
    async def consume(self, namespace: str, key: str) -> dict[str, Any] | None: ...
    async def add_once(self, namespace: str, key: str, ttl_seconds: int) -> bool: ...


class InMemoryEphemeralStore:
    """Test/development only; it is process-local and not suitable for production."""

    def __init__(self) -> None:
        self._records: dict[str, tuple[datetime, dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _name(namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    async def put(self, namespace: str, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        async with self._lock:
            self._records[self._name(namespace, key)] = (expires, value)

    async def consume(self, namespace: str, key: str) -> dict[str, Any] | None:
        name = self._name(namespace, key)
        async with self._lock:
            record = self._records.pop(name, None)
            if record is None or record[0] <= datetime.now(timezone.utc):
                return None
            return record[1]

    async def add_once(self, namespace: str, key: str, ttl_seconds: int) -> bool:
        name = self._name(namespace, key)
        expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        async with self._lock:
            existing = self._records.get(name)
            if existing is not None and existing[0] > datetime.now(timezone.utc):
                return False
            self._records[name] = (expires, {"seen": True})
            return True


class RedisEphemeralStore:
    """Redis implementation with SET NX and GETDEL semantics for distributed safety."""

    def __init__(self, redis_url: str, key_prefix: str = "datasense:security") -> None:
        try:
            from redis.asyncio import Redis
        except ImportError as exc:  # pragma: no cover - dependency configuration error
            raise RuntimeError("redis package is required for RedisEphemeralStore") from exc
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix

    def _name(self, namespace: str, key: str) -> str:
        return f"{self._key_prefix}:{namespace}:{key}"

    async def put(self, namespace: str, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        await self._redis.set(self._name(namespace, key), json.dumps(value, separators=(",", ":")), ex=ttl_seconds)

    async def consume(self, namespace: str, key: str) -> dict[str, Any] | None:
        # GETDEL prevents concurrent ACS/token calls from consuming the same item.
        raw = await self._redis.execute_command("GETDEL", self._name(namespace, key))
        return json.loads(raw) if raw else None

    async def add_once(self, namespace: str, key: str, ttl_seconds: int) -> bool:
        result = await self._redis.set(self._name(namespace, key), "1", ex=ttl_seconds, nx=True)
        return bool(result)

    async def close(self) -> None:
        await self._redis.aclose()
