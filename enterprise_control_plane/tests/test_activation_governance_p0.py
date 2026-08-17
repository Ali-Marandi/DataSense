from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from enterprise_control_plane.app.activation_circuit import (
    ActivationCircuitService,
    CircuitApproval,
    CircuitSnapshot,
    CircuitState,
)
from enterprise_control_plane.app.activation_execution import ActivationExecutionLedger, ExecutionReservation
from enterprise_control_plane.app.activation_payload import ActivationPayloadError, validate_activation_payload
from enterprise_control_plane.app.activation_policy import DeliveryEligibilityService
from enterprise_control_plane.app.outbox import DeliveryResult, OutboxEvent, OutboxStats, OutboxWorker


def run(coro):
    return asyncio.run(coro)


def activation_event(*, organization_id: str = "org-a", channel: str = "external") -> OutboxEvent:
    return OutboxEvent(
        event_id="event-1",
        organization_id=organization_id,
        event_type="activation.case_ready",
        payload={
            "version": 1,
            "case_id": "a" * 64,
            "scope": "activation.external",
            "channel": channel,
            "recipient_ref": "b" * 64,
            "execution_key": "c" * 64,
            "policy_allowed": True,
            "recipient_verified": True,
            "trigger_version": 1,
            "policy_version": 1,
            "correlation_id": "00000000-0000-0000-0000-000000000001",
        },
        attempts=1,
        idempotency_key="activation-event-1",
    )


class MemoryCircuitRepository:
    def __init__(self, state: CircuitState = CircuitState.CLOSED) -> None:
        self.snapshot = CircuitSnapshot("org-a", "activation.external", state, 0, "provisioned")
        self.approvals: list[CircuitApproval] = []
        self.probes: dict[tuple[str, str, datetime], int] = {}

    async def get_activation_circuit(self, *, organization_id: str, scope: str):
        if (organization_id, scope) != (self.snapshot.organization_id, self.snapshot.scope):
            return None
        return self.snapshot

    async def compare_and_set_activation_circuit(self, *, organization_id, scope, expected_version, target_state, reason_code, opened_at):
        if self.snapshot.version != expected_version:
            return None
        self.snapshot = CircuitSnapshot(organization_id, scope, target_state, expected_version + 1, reason_code, opened_at)
        return self.snapshot

    async def record_activation_circuit_approval(self, approval):
        self.approvals.append(approval)

    async def try_consume_half_open_probe(self, *, organization_id, scope, window_started_at, max_attempts):
        key = (organization_id, scope, window_started_at)
        current = self.probes.get(key, 0)
        if current >= max_attempts:
            return False
        self.probes[key] = current + 1
        return True


def test_c03_half_open_requires_approval_is_rate_limited_and_persists():
    repository = MemoryCircuitRepository()
    service = ActivationCircuitService(repository)
    run(service.open(organization_id="org-a", scope="activation.external", reason_code="outbox_lag_critical"))
    approval = CircuitApproval(
        organization_id="org-a", scope="activation.external", transition="open_to_half_open",
        approved_by="sre@example", approval_reference="change-123", approved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert run(service.enter_half_open(approval=approval)).state == CircuitState.HALF_OPEN
    decisions = [run(service.allow_external_attempt(organization_id="org-a", scope="activation.external", now=datetime(2026, 1, 1, 1, 1, tzinfo=timezone.utc))) for _ in range(6)]
    assert [allowed for allowed, _ in decisions] == [True, True, True, True, True, False]
    assert decisions[-1][1] == "suppressed_half_open_rate_limited"
    restarted = ActivationCircuitService(repository)
    assert run(restarted.state_for(organization_id="org-a", scope="activation.external")).state == CircuitState.HALF_OPEN
    assert run(restarted.close(approval=CircuitApproval("org-a", "activation.external", "half_open_to_closed", "sre@example", "change-124", datetime(2026, 1, 1, tzinfo=timezone.utc)), health_proven=False)).state == CircuitState.HALF_OPEN


class MemoryPolicyRepository:
    def __init__(self, *, consent: bool | None = True, kills: dict[str, bool | None] | None = None) -> None:
        self.consent = consent
        self.kills = kills or {}

    async def activation_tenant_kill_enabled(self, *, organization_id: str, scope: str):
        return self.kills.get(organization_id)

    async def activation_consent_granted(self, *, organization_id: str, recipient_ref: str, channel: str):
        return self.consent


class MemoryOutboxRepository:
    def __init__(self, events: list[OutboxEvent]) -> None:
        self.events = list(events)
        self.sent: list[str] = []
        self.suppressed: list[tuple[str, str]] = []
        self.dead: list[tuple[str, str]] = []

    async def recover_stale_leases(self, *, now):
        return 0

    async def claim(self, *, worker_id, limit, lease_until):
        claimed, self.events = self.events[:limit], self.events[limit:]
        return claimed

    async def mark_sent(self, event_id):
        self.sent.append(event_id)

    async def mark_retry(self, event_id, *, next_attempt_at, error_code):
        raise AssertionError("retry is not expected in this test")

    async def mark_dead(self, event_id, *, error_code):
        self.dead.append((event_id, error_code))

    async def mark_suppressed(self, event_id, *, reason_code):
        self.suppressed.append((event_id, reason_code))

    async def stats(self, *, now):
        return OutboxStats(0, 0, len(self.dead), 0)


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def deliver(self, event):
        self.calls += 1
        return DeliveryResult("delivered")


def test_c05_revocation_after_claim_suppresses_without_provider_effect():
    event = activation_event()
    repository = MemoryOutboxRepository([event])
    provider = FakeProvider()
    circuit = ActivationCircuitService(MemoryCircuitRepository())
    policy = DeliveryEligibilityService(MemoryPolicyRepository(consent=False, kills={"org-a": False}), circuit)
    worker = OutboxWorker(repository, provider, policy_evaluator=policy)

    assert run(worker.process_once("worker-a")) == 1
    assert provider.calls == 0
    assert repository.suppressed == [("event-1", "suppressed_consent_revoked")]


class MemoryExecutionRepository:
    def __init__(self, state: str = "effect_recorded") -> None:
        self.state = state
        self.transitions: list[str] = []

    async def begin_activation_execution(self, *, organization_id, execution_key, provider_idempotency_key):
        return ExecutionReservation(self.state, provider_idempotency_key)

    async def record_activation_execution_state(self, *, organization_id, execution_key, target_state, reason_code=None):
        self.transitions.append(target_state)


def test_c08_recovered_execution_with_effect_ledger_skips_provider_duplicate():
    repository = MemoryOutboxRepository([activation_event()])
    provider = FakeProvider()
    worker = OutboxWorker(repository, provider, execution_ledger=ActivationExecutionLedger(MemoryExecutionRepository()))

    assert run(worker.process_once("replacement-worker")) == 1
    assert provider.calls == 0
    assert repository.sent == ["event-1"]


def test_c11_schema_firewall_rejects_raw_like_payload_without_echoing_it():
    raw_email = "customer@example.invalid"
    payload = activation_event().payload | {"email": raw_email}
    with pytest.raises(ActivationPayloadError) as error:
        validate_activation_payload(payload)
    assert error.value.reason_code == "unknown_field"
    assert raw_email not in str(error.value)


def test_c13_tenant_kill_is_isolated_and_unknown_tenant_fails_closed():
    circuit = ActivationCircuitService(MemoryCircuitRepository())
    policy = DeliveryEligibilityService(MemoryPolicyRepository(kills={"org-a": True, "org-b": False}), circuit)
    blocked = run(policy.evaluate_delivery_eligibility(activation_event(organization_id="org-a", channel="in_app")))
    allowed = run(policy.evaluate_delivery_eligibility(activation_event(organization_id="org-b", channel="in_app")))
    unknown = run(policy.evaluate_delivery_eligibility(activation_event(organization_id="org-c", channel="in_app")))
    assert (blocked.allowed, blocked.reason_code) == (False, "suppressed_kill_switch")
    assert (allowed.allowed, allowed.reason_code) == (True, "allowed")
    assert (unknown.allowed, unknown.reason_code) == (False, "suppressed_kill_switch")
