from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from enterprise_control_plane.app.action_gate_rollback import (
    CASRollbackCoordinator,
    ExecutionMode,
    MemoryRollbackRepository,
    RecordingCircuitOutbox,
    RollbackOutcome,
    RollbackTrigger,
    RolloutMode,
    RolloutState,
)
from enterprise_control_plane.app.trust_exchange import (
    Ed25519KeyRecord,
    Ed25519TrustExchangeVerifier,
    KeyStatus,
    MemoryReplayStore,
    MemoryTrustRegistry,
    TrustRelationship,
    build_jws_receipt,
    new_test_private_key,
    public_key_bytes,
    valid_test_payload,
)


NOW = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
ORG_ID = "00000000-0000-0000-0000-000000000001"
SCOPE = "action.external"
POLICY_CURRENT = "sha256:" + "d" * 64
POLICY_SAFE = "sha256:" + "e" * 64


def run(coro):
    return asyncio.run(coro)


async def collect(*coroutines):
    return await asyncio.gather(*coroutines)


def relationship() -> TrustRelationship:
    return TrustRelationship(
        relationship_id="relationship-synthetic-1",
        issuer="urn:datasense:issuer:synthetic",
        receiver_organization_id=ORG_ID,
        environment="staging",
        allowed_action_types=frozenset({"rollback.trigger"}),
    )


def build_exchange(*, private_key, nonce: str, receipt_id: str = "00000000-0000-0000-0000-000000000001"):
    item = relationship()
    payload = valid_test_payload(now=NOW, relationship=item)
    payload["nonce"] = nonce
    payload["receipt_id"] = receipt_id
    return build_jws_receipt(private_key=private_key, key_id="issuer-key-v1", payload=payload)


def verifier(*, key_status: KeyStatus = KeyStatus.ACTIVE, replay_store=None):
    private_key = new_test_private_key()
    record = Ed25519KeyRecord(
        issuer=relationship().issuer,
        key_id="issuer-key-v1",
        public_key=public_key_bytes(private_key),
        status=key_status,
        not_before=NOW - timedelta(days=1),
        not_after=NOW + timedelta(days=1),
        environment="staging",
    )
    return private_key, Ed25519TrustExchangeVerifier(
        MemoryTrustRegistry([relationship()], [record]), replay_store or MemoryReplayStore()
    )


def rollout_state() -> RolloutState:
    return RolloutState(
        organization_id=ORG_ID,
        scope=SCOPE,
        mode=RolloutMode.ENFORCE,
        execution_mode=ExecutionMode.ALLOW_GUARDED,
        active_policy_digest=POLICY_CURRENT,
        last_known_good_policy_digest=POLICY_SAFE,
        version=7,
        gate_epoch=11,
    )


def test_ed25519_exchange_signature_replay_and_revocation_fail_closed():
    private_key, exchange_verifier = verifier()
    envelope = build_exchange(private_key=private_key, nonce="nonce-001")

    first = run(exchange_verifier.verify(
        envelope,
        receiver_organization_id=ORG_ID,
        environment="staging",
        expected_action_type="rollback.trigger",
        now=NOW,
    ))
    second = run(exchange_verifier.verify(
        envelope,
        receiver_organization_id=ORG_ID,
        environment="staging",
        expected_action_type="rollback.trigger",
        now=NOW,
    ))
    assert first.valid is True
    assert first.receipt_digest is not None
    assert second.valid is False
    assert second.reason_code == "exchange_receipt_replayed"

    revoked_private, revoked_verifier = verifier(key_status=KeyStatus.REVOKED)
    revoked = run(revoked_verifier.verify(
        build_exchange(private_key=revoked_private, nonce="nonce-002"),
        receiver_organization_id=ORG_ID,
        environment="staging",
        expected_action_type="rollback.trigger",
        now=NOW,
    ))
    assert revoked.valid is False
    assert revoked.reason_code == "exchange_key_revoked"


def test_tampered_ed25519_payload_never_becomes_a_valid_trigger():
    private_key, exchange_verifier = verifier()
    envelope = build_exchange(private_key=private_key, nonce="nonce-003")
    tampered = dict(envelope)
    # Valid base64url JSON that changes one signed claim but retains the original signature.
    tampered["payload"] = envelope["payload"][:-2] + ("AA" if envelope["payload"][-2:] != "AA" else "BB")
    result = run(exchange_verifier.verify(
        tampered,
        receiver_organization_id=ORG_ID,
        environment="staging",
        expected_action_type="rollback.trigger",
        now=NOW,
    ))
    assert result.valid is False
    assert result.reason_code in {"exchange_signature_invalid", "exchange_verification_failed", "invalid_exchange_payload"}


def test_concurrent_verified_triggers_activate_exactly_one_cas_rollback():
    private_key, exchange_verifier = verifier()
    repository = MemoryRollbackRepository([rollout_state()])
    circuit_outbox = RecordingCircuitOutbox()
    coordinator = CASRollbackCoordinator(repository, exchange_verifier=exchange_verifier, circuit_outbox=circuit_outbox)

    async def activate(index: int):
        envelope = build_exchange(
            private_key=private_key,
            nonce=f"nonce-race-{index:03d}",
            receipt_id=f"00000000-0000-0000-0000-{index:012d}",
        )
        return await coordinator.activate_from_exchange_receipt(
            envelope,
            organization_id=ORG_ID,
            scope=SCOPE,
            receiver_organization_id=ORG_ID,
            environment="staging",
            now=NOW,
        )

    results = run(collect(*(activate(index) for index in range(64))))
    active = [result for result in results if result.outcome == RollbackOutcome.ROLLBACK_ACTIVE]
    contained = [result for result in results if result.outcome == RollbackOutcome.ALREADY_CONTAINED]
    assert len(active) == 1
    assert len(contained) == 63
    assert repository.activation_count == 1
    assert len(circuit_outbox.calls) == 1

    state = run(repository.state_for(ORG_ID, SCOPE))
    assert state is not None
    assert state.execution_mode == ExecutionMode.SUPPRESS_EXTERNAL
    assert state.mode == RolloutMode.ROLLBACK_ACTIVE
    assert state.active_policy_digest == POLICY_SAFE
    assert (state.version, state.gate_epoch) == (8, 12)


def test_same_signed_trigger_is_replay_denied_and_never_retransitions():
    private_key, exchange_verifier = verifier()
    repository = MemoryRollbackRepository([rollout_state()])
    coordinator = CASRollbackCoordinator(repository, exchange_verifier=exchange_verifier)
    envelope = build_exchange(private_key=private_key, nonce="nonce-one-time")

    async def activate_once():
        return await coordinator.activate_from_exchange_receipt(
            envelope,
            organization_id=ORG_ID,
            scope=SCOPE,
            receiver_organization_id=ORG_ID,
            environment="staging",
            now=NOW,
        )

    results = run(collect(*(activate_once() for _ in range(32))))
    assert sum(result.outcome == RollbackOutcome.ROLLBACK_ACTIVE for result in results) == 1
    assert sum(result.outcome == RollbackOutcome.TRIGGER_DENIED for result in results) == 31
    assert repository.activation_count == 1


def test_epoch_fencing_blocks_a_previously_reserved_permit_after_rollback():
    private_key, exchange_verifier = verifier()
    repository = MemoryRollbackRepository([rollout_state()])
    coordinator = CASRollbackCoordinator(repository, exchange_verifier=exchange_verifier)
    permit = run(coordinator.reserve_permit(
        organization_id=ORG_ID,
        scope=SCOPE,
        execution_key="execution-key-0001",
        receipt_digest="sha256:" + "f" * 64,
        expires_at=NOW + timedelta(minutes=5),
    ))
    assert permit is not None
    assert permit.gate_epoch == 11

    rollback = run(coordinator.activate_from_exchange_receipt(
        build_exchange(private_key=private_key, nonce="nonce-fencing"),
        organization_id=ORG_ID,
        scope=SCOPE,
        receiver_organization_id=ORG_ID,
        environment="staging",
        now=NOW,
    ))
    assert rollback.outcome == RollbackOutcome.ROLLBACK_ACTIVE
    assert run(coordinator.commit_permit(permit, now=NOW + timedelta(seconds=1))) is False


def test_circuit_outbox_failure_keeps_authoritative_gate_state_suppressed():
    private_key, exchange_verifier = verifier()
    repository = MemoryRollbackRepository([rollout_state()])
    coordinator = CASRollbackCoordinator(
        repository,
        exchange_verifier=exchange_verifier,
        circuit_outbox=RecordingCircuitOutbox(should_fail=True),
    )
    result = run(coordinator.activate_from_exchange_receipt(
        build_exchange(private_key=private_key, nonce="nonce-outbox-failure"),
        organization_id=ORG_ID,
        scope=SCOPE,
        receiver_organization_id=ORG_ID,
        environment="staging",
        now=NOW,
    ))
    assert result.outcome == RollbackOutcome.CIRCUIT_PENDING
    state = run(repository.state_for(ORG_ID, SCOPE))
    assert state is not None
    assert state.execution_mode == ExecutionMode.SUPPRESS_EXTERNAL
    assert run(coordinator.reserve_permit(
        organization_id=ORG_ID,
        scope=SCOPE,
        execution_key="must-not-reserve",
        receipt_digest="sha256:" + "a" * 64,
        expires_at=NOW + timedelta(minutes=1),
    )) is None


def test_direct_duplicate_trigger_uses_evidence_digest_deduplication():
    repository = MemoryRollbackRepository([rollout_state()])
    coordinator = CASRollbackCoordinator(repository)
    trigger = RollbackTrigger(
        organization_id=ORG_ID,
        scope=SCOPE,
        trigger_type="synthetic_metric",
        reason_code="synthetic_burn_rate",
        evidence_digest="sha256:" + "1" * 64,
        observed_at=NOW,
    )
    results = run(collect(*(coordinator.activate(trigger) for _ in range(40))))
    assert sum(result.outcome == RollbackOutcome.ROLLBACK_ACTIVE for result in results) == 1
    assert sum(result.outcome == RollbackOutcome.ALREADY_HANDLED for result in results) == 39
    assert repository.activation_count == 1
