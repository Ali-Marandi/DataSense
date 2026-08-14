from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from enterprise_control_plane.app.models import Permission, Principal
from enterprise_control_plane.app.outbox import DeliveryResult, OutboxEvent, OutboxStats, OutboxWorker
from enterprise_control_plane.app.quality_gate import QualityGateObservation, QualityGateService


def run(coro):
    return asyncio.run(coro)


class MemoryOutboxRepository:
    def __init__(self, events: list[OutboxEvent], *, recovered: int = 0) -> None:
        self.events = list(events)
        self.recovered = recovered
        self.sent: list[str] = []
        self.retried: list[tuple[str, str]] = []
        self.dead: list[tuple[str, str]] = []

    async def recover_stale_leases(self, *, now: datetime) -> int:
        return self.recovered

    async def claim(self, *, worker_id: str, limit: int, lease_until: datetime) -> list[OutboxEvent]:
        claimed, self.events = self.events[:limit], self.events[limit:]
        return claimed

    async def mark_sent(self, event_id: str) -> None:
        self.sent.append(event_id)

    async def mark_retry(self, event_id: str, *, next_attempt_at: datetime, error_code: str) -> None:
        self.retried.append((event_id, error_code))

    async def mark_dead(self, event_id: str, *, error_code: str) -> None:
        self.dead.append((event_id, error_code))

    async def stats(self, *, now: datetime) -> OutboxStats:
        return OutboxStats(pending=len(self.events), processing=0, dead=len(self.dead), oldest_pending_age_seconds=0)


class ResultDelivery:
    def __init__(self, result: DeliveryResult) -> None:
        self.result = result

    async def deliver(self, event: OutboxEvent) -> DeliveryResult:
        return self.result


def event(*, attempts: int = 1) -> OutboxEvent:
    return OutboxEvent(
        event_id="event-1", organization_id="org-1", event_type="quality_gate.blocked",
        payload={"version": 1, "decision": "blocked"}, attempts=attempts, idempotency_key="key-1",
    )


def test_outbox_worker_retries_transient_delivery_and_recovers_stale_leases():
    repository = MemoryOutboxRepository([event()], recovered=2)
    worker = OutboxWorker(repository, ResultDelivery(DeliveryResult("retry", "webhook_timeout")), retry_base_seconds=1)

    assert run(worker.process_once("worker-a", now=datetime(2026, 1, 1, tzinfo=timezone.utc))) == 1
    assert repository.retried == [("event-1", "webhook_timeout")]
    assert repository.sent == []
    assert repository.dead == []


def test_outbox_worker_dead_letters_permanent_or_exhausted_delivery():
    permanent = MemoryOutboxRepository([event()])
    worker = OutboxWorker(permanent, ResultDelivery(DeliveryResult("permanent_failure", "webhook_http_400")))
    run(worker.process_once("worker-a"))
    assert permanent.dead == [("event-1", "webhook_http_400")]

    exhausted = MemoryOutboxRepository([event(attempts=8)])
    worker = OutboxWorker(exhausted, ResultDelivery(DeliveryResult("retry", "webhook_timeout")), max_attempts=8)
    run(worker.process_once("worker-a"))
    assert exhausted.dead == [("event-1", "webhook_timeout")]


class MemoryQualityRepository:
    def __init__(self) -> None:
        self.seen: set[tuple[str, str]] = set()
        self.records: list[QualityGateObservation] = []

    async def record_quality_gate_observation(self, *, organization_id: str, actor_subject: str, observation: QualityGateObservation) -> bool:
        key = (organization_id, observation.execution_id)
        if key in self.seen:
            return False
        self.seen.add(key)
        self.records.append(observation)
        return True


def test_quality_gate_hook_is_idempotent_and_accepts_metadata_only_evidence():
    repository = MemoryQualityRepository()
    service = QualityGateService(repository)
    principal = Principal("subject-1", "org-1", "membership-1", frozenset({Permission.CONTRACT_RUN}))
    observation = QualityGateObservation(
        execution_id="quality-run-0001", contract_fingerprint="a" * 64, policy_tier="tier_1",
        decision="blocked", score=94.5, critical_failures=1, rows=1000,
    )

    assert run(service.record(principal, observation)) is True
    assert run(service.record(principal, observation)) is False
    assert repository.records == [observation]
