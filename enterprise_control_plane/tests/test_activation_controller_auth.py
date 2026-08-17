from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from enterprise_control_plane.app.activation_circuit import ActivationCircuitService, CircuitSnapshot, CircuitState
from enterprise_control_plane.app.activation_controller import ActivationAlertController, AlertVerificationError
from enterprise_control_plane.app.ephemeral_store import InMemoryEphemeralStore


def run(coro):
    return asyncio.run(coro)


class AlertCircuitRepository:
    organization_id = "00000000-0000-0000-0000-000000000001"
    scope = "activation.external"

    def __init__(self) -> None:
        self.snapshot = CircuitSnapshot(self.organization_id, self.scope, CircuitState.CLOSED, 0, "provisioned")

    async def get_activation_circuit(self, *, organization_id, scope):
        return self.snapshot if (organization_id, scope) == (self.organization_id, self.scope) else None

    async def compare_and_set_activation_circuit(self, *, organization_id, scope, expected_version, target_state, reason_code, opened_at):
        if expected_version != self.snapshot.version:
            return None
        self.snapshot = CircuitSnapshot(organization_id, scope, target_state, expected_version + 1, reason_code, opened_at)
        return self.snapshot

    async def record_activation_circuit_approval(self, approval):
        raise AssertionError("alert receiver never records approval")

    async def try_consume_half_open_probe(self, **kwargs):
        raise AssertionError("alert receiver only opens a circuit")


def payload(*, timestamp: int, nonce: str = "nonce_0000000001"):
    return {
        "alert_name": "activation_outbox_lag_critical",
        "environment": "staging",
        "organization_id": AlertCircuitRepository.organization_id,
        "scope": AlertCircuitRepository.scope,
        "timestamp": timestamp,
        "nonce": nonce,
    }


def controller() -> ActivationAlertController:
    return ActivationAlertController(
        hmac_key="test-alert-key",
        nonce_store=InMemoryEphemeralStore(),
        circuit=ActivationCircuitService(AlertCircuitRepository()),
        environment="staging",
    )


def test_c14_only_signed_fresh_allowlisted_alert_opens_circuit_and_replay_is_rejected():
    instance = controller()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    body = payload(timestamp=int(now.timestamp()))
    signature = ActivationAlertController.signature_for("test-alert-key", body)

    snapshot = run(instance.receive(raw_body=ActivationAlertController.canonical_body(body), signature=signature, now=now))
    assert snapshot.state == CircuitState.OPEN

    with pytest.raises(AlertVerificationError) as replay:
        run(instance.receive(raw_body=ActivationAlertController.canonical_body(body), signature=signature, now=now))
    assert (replay.value.status_code, replay.value.reason_code) == (409, "replayed_alert")


def test_c14_forged_or_stale_alert_never_opens_circuit():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    forged = controller()
    body = payload(timestamp=int(now.timestamp()), nonce="nonce_0000000002")
    with pytest.raises(AlertVerificationError) as invalid:
        run(forged.receive(raw_body=ActivationAlertController.canonical_body(body), signature="sha256=" + "0" * 64, now=now))
    assert (invalid.value.status_code, invalid.value.reason_code) == (401, "invalid_alert_signature")

    stale = controller()
    old = payload(timestamp=int(now.timestamp()) - 301, nonce="nonce_0000000003")
    old_signature = ActivationAlertController.signature_for("test-alert-key", old)
    with pytest.raises(AlertVerificationError) as rejected:
        run(stale.receive(raw_body=ActivationAlertController.canonical_body(old), signature=old_signature, now=now))
    assert (rejected.value.status_code, rejected.value.reason_code) == (401, "stale_alert")
