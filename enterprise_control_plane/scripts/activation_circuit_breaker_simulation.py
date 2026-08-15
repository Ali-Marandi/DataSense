"""Non-production simulation harness for activation circuit-breaker invariants.

This is intentionally a pure, in-memory model. It does not connect to Kubernetes,
PostgreSQL, Alertmanager, webhook providers, or customer data. Running it requires an
explicit non-production environment acknowledgement.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    MANUAL_KILL = "manual_kill"
    UNKNOWN = "unknown"


class Decision(StrEnum):
    DELIVER = "deliver"
    SUPPRESS_CIRCUIT_OPEN = "suppress_circuit_open"
    SUPPRESS_KILL_SWITCH = "suppress_kill_switch"
    SUPPRESS_POLICY_DENIED = "suppress_policy_denied"
    SUPPRESS_RECIPIENT_UNVERIFIED = "suppress_recipient_unverified"
    SUPPRESS_UNKNOWN = "suppress_unknown"
    IDEMPOTENT_SKIP = "idempotent_skip"


@dataclass(frozen=True)
class ActivationRequest:
    execution_key: str
    channel: Literal["in_app", "external"]
    policy_allowed: bool = True
    recipient_verified: bool = True


@dataclass
class SimulationResult:
    decision: Decision
    external_effects: int


@dataclass
class ActivationCircuitModel:
    state: CircuitState = CircuitState.CLOSED
    audit_codes: list[str] = field(default_factory=list)
    delivered_execution_keys: set[str] = field(default_factory=set)
    external_effects: int = 0

    def open_for_lag(self) -> None:
        """A critical lag alert may only open the circuit; it cannot close it."""
        if self.state != CircuitState.MANUAL_KILL:
            self.state = CircuitState.OPEN
            self.audit_codes.append("outbox_lag_critical")

    def activate_manual_kill(self) -> None:
        self.state = CircuitState.MANUAL_KILL
        self.audit_codes.append("manual_kill")

    def enter_half_open(self, *, approved: bool) -> bool:
        if self.state != CircuitState.OPEN or not approved:
            self.audit_codes.append("half_open_denied")
            return False
        self.state = CircuitState.HALF_OPEN
        self.audit_codes.append("half_open_approved")
        return True

    def close(self, *, approved: bool, health_proven: bool) -> bool:
        """Closing is deliberately two-condition and never automatic."""
        if self.state != CircuitState.HALF_OPEN or not approved or not health_proven:
            self.audit_codes.append("close_denied")
            return False
        self.state = CircuitState.CLOSED
        self.audit_codes.append("close_approved")
        return True

    def deliver(self, request: ActivationRequest) -> SimulationResult:
        if self.state == CircuitState.MANUAL_KILL:
            return SimulationResult(Decision.SUPPRESS_KILL_SWITCH, self.external_effects)
        if self.state in {CircuitState.OPEN, CircuitState.HALF_OPEN} and request.channel == "external":
            return SimulationResult(Decision.SUPPRESS_CIRCUIT_OPEN, self.external_effects)
        if self.state == CircuitState.UNKNOWN:
            return SimulationResult(Decision.SUPPRESS_UNKNOWN, self.external_effects)
        if not request.policy_allowed:
            return SimulationResult(Decision.SUPPRESS_POLICY_DENIED, self.external_effects)
        if request.channel == "external" and not request.recipient_verified:
            return SimulationResult(Decision.SUPPRESS_RECIPIENT_UNVERIFIED, self.external_effects)
        if request.execution_key in self.delivered_execution_keys:
            return SimulationResult(Decision.IDEMPOTENT_SKIP, self.external_effects)
        self.delivered_execution_keys.add(request.execution_key)
        if request.channel == "external":
            self.external_effects += 1
        return SimulationResult(Decision.DELIVER, self.external_effects)


def run_scenarios() -> None:
    model = ActivationCircuitModel()
    allowed = ActivationRequest("case-1:trigger:v1", "external")
    assert model.deliver(allowed).decision == Decision.DELIVER
    assert model.external_effects == 1
    assert model.deliver(allowed).decision == Decision.IDEMPOTENT_SKIP
    assert model.external_effects == 1

    model.open_for_lag()
    assert model.state == CircuitState.OPEN
    assert model.deliver(ActivationRequest("case-2:trigger:v1", "external")).decision == Decision.SUPPRESS_CIRCUIT_OPEN
    assert model.external_effects == 1
    assert model.close(approved=True, health_proven=True) is False
    assert model.enter_half_open(approved=True) is True
    assert model.deliver(ActivationRequest("case-3:trigger:v1", "external")).decision == Decision.SUPPRESS_CIRCUIT_OPEN
    assert model.close(approved=True, health_proven=True) is True

    assert model.deliver(ActivationRequest("case-4:trigger:v1", "external", policy_allowed=False)).decision == Decision.SUPPRESS_POLICY_DENIED
    assert model.deliver(ActivationRequest("case-5:trigger:v1", "external", recipient_verified=False)).decision == Decision.SUPPRESS_RECIPIENT_UNVERIFIED
    model.activate_manual_kill()
    assert model.deliver(ActivationRequest("case-6:trigger:v1", "external")).decision == Decision.SUPPRESS_KILL_SWITCH
    assert model.external_effects == 1
    print("PASS: non-production activation circuit-breaker simulations passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run non-production activation circuit-breaker simulations.")
    parser.add_argument("--environment", required=True, choices=("test", "staging"))
    parser.add_argument("--confirm-nonprod", action="store_true")
    args = parser.parse_args()
    if not args.confirm_nonprod:
        raise SystemExit("Refusing to run without --confirm-nonprod")
    run_scenarios()


if __name__ == "__main__":
    main()
