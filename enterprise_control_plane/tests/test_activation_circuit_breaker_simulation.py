from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from activation_circuit_breaker_simulation import (  # noqa: E402
    ActivationCircuitModel,
    ActivationRequest,
    CircuitState,
    Decision,
)


def test_lag_opens_circuit_and_prevents_external_effects_until_manual_close():
    model = ActivationCircuitModel()
    first = model.deliver(ActivationRequest("case-1:v1", "external"))
    assert first.decision == Decision.DELIVER
    assert first.external_effects == 1

    model.open_for_lag()
    assert model.state == CircuitState.OPEN
    result = model.deliver(ActivationRequest("case-2:v1", "external"))
    assert result.decision == Decision.SUPPRESS_CIRCUIT_OPEN
    assert result.external_effects == 1

    # Healthy signals alone cannot resume customer-facing delivery.
    assert model.close(approved=True, health_proven=True) is False
    assert model.enter_half_open(approved=True) is True
    assert model.deliver(ActivationRequest("case-3:v1", "external")).decision == Decision.SUPPRESS_CIRCUIT_OPEN
    assert model.close(approved=True, health_proven=True) is True
    assert model.state == CircuitState.CLOSED


def test_policy_recipient_and_kill_switch_fail_closed_without_external_effects():
    model = ActivationCircuitModel()
    assert model.deliver(ActivationRequest("case-policy:v1", "external", policy_allowed=False)).decision == Decision.SUPPRESS_POLICY_DENIED
    assert model.deliver(ActivationRequest("case-recipient:v1", "external", recipient_verified=False)).decision == Decision.SUPPRESS_RECIPIENT_UNVERIFIED

    model.state = CircuitState.UNKNOWN
    assert model.deliver(ActivationRequest("case-unknown:v1", "external")).decision == Decision.SUPPRESS_UNKNOWN

    model.activate_manual_kill()
    assert model.deliver(ActivationRequest("case-kill:v1", "external")).decision == Decision.SUPPRESS_KILL_SWITCH
    assert model.external_effects == 0


def test_duplicate_delivery_has_at_most_one_external_effect():
    model = ActivationCircuitModel()
    request = ActivationRequest("case-duplicate:v1", "external")
    assert model.deliver(request).decision == Decision.DELIVER
    assert model.deliver(request).decision == Decision.IDEMPOTENT_SKIP
    assert model.external_effects == 1


def test_lag_never_overrides_manual_kill_state():
    model = ActivationCircuitModel()
    model.activate_manual_kill()
    model.open_for_lag()
    assert model.state == CircuitState.MANUAL_KILL
