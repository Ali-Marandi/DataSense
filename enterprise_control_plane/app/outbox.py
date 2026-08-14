"""Transactional-outbox worker primitives.

The database repository owns atomic claiming and state transitions. This module owns delivery
classification, bounded retry timing and metric emission; it never logs payloads.
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Protocol

from .metrics import (
    OUTBOX_DEAD,
    OUTBOX_DELIVERIES,
    OUTBOX_LEASE_RECOVERIES,
    OUTBOX_OLDEST_PENDING_SECONDS,
    OUTBOX_PENDING,
    OUTBOX_PROCESSING_LEASES,
)


@dataclass(frozen=True)
class OutboxEvent:
    event_id: str
    organization_id: str
    event_type: str
    payload: dict[str, object]
    attempts: int
    idempotency_key: str


@dataclass(frozen=True)
class OutboxStats:
    pending: int
    processing: int
    dead: int
    oldest_pending_age_seconds: float


@dataclass(frozen=True)
class DeliveryResult:
    outcome: Literal["delivered", "retry", "permanent_failure"]
    error_code: str | None = None


class DeliveryClient(Protocol):
    async def deliver(self, event: OutboxEvent) -> DeliveryResult: ...


class OutboxRepository(Protocol):
    async def recover_stale_leases(self, *, now: datetime) -> int: ...
    async def claim(self, *, worker_id: str, limit: int, lease_until: datetime) -> list[OutboxEvent]: ...
    async def mark_sent(self, event_id: str) -> None: ...
    async def mark_retry(self, event_id: str, *, next_attempt_at: datetime, error_code: str) -> None: ...
    async def mark_dead(self, event_id: str, *, error_code: str) -> None: ...
    async def stats(self, *, now: datetime) -> OutboxStats: ...


class OutboxWorker:
    """Executes bounded batches and relies on the repository for atomic state transitions."""

    def __init__(
        self,
        repository: OutboxRepository,
        delivery_client: DeliveryClient,
        *,
        batch_size: int = 25,
        lease_seconds: int = 60,
        max_attempts: int = 8,
        retry_base_seconds: int = 5,
        retry_cap_seconds: int = 900,
    ) -> None:
        if batch_size < 1 or lease_seconds < 1 or max_attempts < 1:
            raise ValueError("worker limits must be positive")
        self.repository = repository
        self.delivery_client = delivery_client
        self.batch_size = batch_size
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts
        self.retry_base_seconds = retry_base_seconds
        self.retry_cap_seconds = retry_cap_seconds

    def _retry_at(self, attempts: int, now: datetime) -> datetime:
        """Exponential backoff with bounded jitter to avoid synchronized retry storms."""
        ceiling = min(self.retry_cap_seconds, self.retry_base_seconds * (2 ** max(attempts - 1, 0)))
        return now + timedelta(seconds=ceiling + random.uniform(0, max(ceiling * 0.1, 1)))

    async def refresh_metrics(self, now: datetime | None = None) -> OutboxStats:
        stats = await self.repository.stats(now=now or datetime.now(timezone.utc))
        OUTBOX_PENDING.set(stats.pending)
        OUTBOX_PROCESSING_LEASES.set(stats.processing)
        OUTBOX_DEAD.set(stats.dead)
        OUTBOX_OLDEST_PENDING_SECONDS.set(max(stats.oldest_pending_age_seconds, 0))
        return stats

    async def process_once(self, worker_id: str, *, now: datetime | None = None) -> int:
        """Recover abandoned claims, deliver one bounded batch, and refresh aggregate gauges."""
        now = now or datetime.now(timezone.utc)
        recovered = await self.repository.recover_stale_leases(now=now)
        if recovered:
            OUTBOX_LEASE_RECOVERIES.inc(recovered)

        events = await self.repository.claim(
            worker_id=worker_id,
            limit=self.batch_size,
            lease_until=now + timedelta(seconds=self.lease_seconds),
        )
        for event in events:
            try:
                result = await self.delivery_client.deliver(event)
            except Exception:
                # Do not place exception text in metrics, event payload or logs; map it to a stable code.
                result = DeliveryResult("retry", "delivery_exception")

            if result.outcome == "delivered":
                await self.repository.mark_sent(event.event_id)
                OUTBOX_DELIVERIES.labels(event_type=event.event_type, outcome="delivered").inc()
                continue

            error_code = result.error_code or "delivery_failed"
            if result.outcome == "permanent_failure" or event.attempts >= self.max_attempts:
                await self.repository.mark_dead(event.event_id, error_code=error_code)
                OUTBOX_DELIVERIES.labels(event_type=event.event_type, outcome="dead").inc()
                continue

            await self.repository.mark_retry(
                event.event_id,
                next_attempt_at=self._retry_at(event.attempts, now),
                error_code=error_code,
            )
            OUTBOX_DELIVERIES.labels(event_type=event.event_type, outcome="retry").inc()

        await self.refresh_metrics(now)
        return len(events)

    async def run_forever(self, worker_id: str, *, poll_interval_seconds: float = 2.0) -> None:
        """Run until cancelled; graceful Kubernetes shutdown cancels this coroutine."""
        while True:
            processed = await self.process_once(worker_id)
            if processed == 0:
                await asyncio.sleep(poll_interval_seconds)
