"""Fail-closed policy checks performed immediately before activation delivery."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .activation_circuit import ActivationCircuitService
from .outbox import OutboxEvent


@dataclass(frozen=True)
class DeliveryEligibility:
    allowed: bool
    reason_code: str


class ActivationPolicyRepository(Protocol):
    async def activation_tenant_kill_enabled(self, *, organization_id: str, scope: str) -> bool | None: ...
    async def activation_consent_granted(self, *, organization_id: str, recipient_ref: str, channel: str) -> bool | None: ...


class DeliveryEligibilityService:
    """Rechecks mutable policy state after claim and before any provider invocation.

    A missing record, unavailable dependency, malformed activation metadata, or unknown circuit
    returns a stable deny code.  The caller must turn denials into terminal suppression rather
    than retrying or dead-lettering them.
    """

    def __init__(self, repository: ActivationPolicyRepository, circuit: ActivationCircuitService) -> None:
        self.repository = repository
        self.circuit = circuit

    async def evaluate_delivery_eligibility(self, event: OutboxEvent) -> DeliveryEligibility:
        if not event.event_type.startswith("activation."):
            return DeliveryEligibility(True, "not_activation_event")

        payload = event.payload
        required = ("scope", "channel", "recipient_ref", "policy_allowed", "recipient_verified")
        if any(key not in payload for key in required):
            return DeliveryEligibility(False, "suppressed_payload_invalid")
        scope = payload["scope"]
        channel = payload["channel"]
        recipient_ref = payload["recipient_ref"]
        if not isinstance(scope, str) or not isinstance(channel, str) or not isinstance(recipient_ref, str):
            return DeliveryEligibility(False, "suppressed_payload_invalid")
        if payload["policy_allowed"] is not True:
            return DeliveryEligibility(False, "suppressed_policy_denied")
        if channel not in {"in_app", "external"}:
            return DeliveryEligibility(False, "suppressed_payload_invalid")
        if payload["recipient_verified"] is not True:
            return DeliveryEligibility(False, "suppressed_recipient_unverified")

        try:
            kill_enabled = await self.repository.activation_tenant_kill_enabled(
                organization_id=event.organization_id, scope=scope
            )
        except Exception:
            kill_enabled = None
        if kill_enabled is not False:
            return DeliveryEligibility(False, "suppressed_kill_switch")

        if channel == "external":
            try:
                consent_granted = await self.repository.activation_consent_granted(
                    organization_id=event.organization_id, recipient_ref=recipient_ref, channel=channel
                )
            except Exception:
                consent_granted = None
            if consent_granted is not True:
                return DeliveryEligibility(False, "suppressed_consent_revoked")

            allowed, reason_code = await self.circuit.allow_external_attempt(
                organization_id=event.organization_id, scope=scope
            )
            if not allowed:
                return DeliveryEligibility(False, reason_code)

        return DeliveryEligibility(True, "allowed")
