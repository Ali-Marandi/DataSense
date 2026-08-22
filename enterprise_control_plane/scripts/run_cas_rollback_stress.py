#!/usr/bin/env python3
"""Run a synthetic-only 64-trigger concurrency test for the CAS rollback reference.

This script has no network, provider, database, or Kubernetes side effect.  It validates the
same safe-state and fencing invariants that a PostgreSQL integration test must enforce with
row locks, version checks, and a transactional outbox.
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from time import perf_counter

from enterprise_control_plane.app.action_gate_rollback import (
    ExecutionMode,
    MemoryRollbackRepository,
    RolloutMode,
    RolloutState,
    TrustExchangeRollbackIngress,
)
from enterprise_control_plane.app.ephemeral_store import InMemoryEphemeralStore
from enterprise_control_plane.app.trust_exchange import (
    Ed25519KeyRecord,
    KeyStatus,
    MemoryTrustRegistry,
    TrustRelationship,
    build_jws_receipt,
    new_test_private_key,
    public_key_bytes,
    valid_test_payload,
)


ORGANIZATION_ID = "00000000-0000-0000-0000-000000000001"
SCOPE = "action.external"
NOW = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


async def run_stress(concurrency: int = 64) -> dict[str, object]:
    if concurrency < 2 or concurrency > 512:
        raise ValueError("concurrency must be between 2 and 512")
    relationship = TrustRelationship(
        relationship_id="relationship-synthetic-stress",
        issuer="urn:datasense:issuer:synthetic",
        receiver_organization_id=ORGANIZATION_ID,
        environment="staging",
        allowed_action_types=frozenset({"rollback.trigger"}),
    )
    private_key = new_test_private_key()
    registry = MemoryTrustRegistry([relationship], [Ed25519KeyRecord(
        issuer=relationship.issuer,
        key_id="issuer-key-stress-v1",
        public_key=public_key_bytes(private_key),
        status=KeyStatus.ACTIVE,
        not_before=NOW - timedelta(days=1),
        not_after=NOW + timedelta(days=1),
        environment="staging",
    )])
    repository = MemoryRollbackRepository([RolloutState(
        organization_id=ORGANIZATION_ID,
        scope=SCOPE,
        mode=RolloutMode.ENFORCE,
        execution_mode=ExecutionMode.ALLOW_GUARDED,
        active_policy_digest="sha256:" + "a" * 64,
        last_known_good_policy_digest="sha256:" + "b" * 64,
        version=9,
        gate_epoch=21,
    )])
    ingress = TrustExchangeRollbackIngress(
        repository=repository,
        registry_factory=lambda _organization_id: registry,
        replay_store=InMemoryEphemeralStore(),
        receiver_organization_id=ORGANIZATION_ID,
        environment="staging",
        allowed_scopes=frozenset({SCOPE}),
    )

    async def one(index: int):
        payload = valid_test_payload(now=NOW, relationship=relationship)
        payload["receipt_id"] = f"00000000-0000-0000-0000-{index:012d}"
        payload["nonce"] = f"stress-nonce-{index:03d}"
        envelope = build_jws_receipt(private_key=private_key, key_id="issuer-key-stress-v1", payload=payload)
        return await ingress.receive(scope=SCOPE, envelope=envelope, now=NOW)

    started = perf_counter()
    results = await asyncio.gather(*(one(index) for index in range(concurrency)))
    duration_ms = round((perf_counter() - started) * 1_000, 3)
    state = await repository.state_for(ORGANIZATION_ID, SCOPE)
    assert state is not None
    counts = Counter(result.outcome.value for result in results)
    report = {
        "scenario": "synthetic_64_concurrent_ed25519_cas_rollback",
        "concurrency": concurrency,
        "duration_ms": duration_ms,
        "outcomes": dict(sorted(counts.items())),
        "activation_count": repository.activation_count,
        "final_mode": state.mode.value,
        "final_execution_mode": state.execution_mode.value,
        "final_version": state.version,
        "final_gate_epoch": state.gate_epoch,
        "invariants": {
            "exactly_one_rollback": counts.get("rollback_active", 0) == 1 and repository.activation_count == 1,
            "all_other_triggers_contained": counts.get("already_contained", 0) == concurrency - 1,
            "external_effects_suppressed": state.execution_mode == ExecutionMode.SUPPRESS_EXTERNAL,
            "epoch_advanced_once": state.gate_epoch == 22 and state.version == 10,
        },
    }
    if not all(report["invariants"].values()):
        raise AssertionError(json.dumps(report, sort_keys=True))
    return report


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run_stress()), sort_keys=True))
