"""Execution ledger for activation delivery recovery and idempotent provider effects."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .activation_payload import ActivationPayload, validate_activation_payload
from .outbox import OutboxEvent, PolicyDecision


ExecutionState = Literal["started", "effect_recorded", "suppressed", "failed"]


@dataclass(frozen=True)
class ExecutionReservation:
    state: ExecutionState
    provider_idempotency_key: str


class ActivationExecutionRepository(Protocol):
    async def begin_activation_execution(
        self,
        *,
        organization_id: str,
        execution_key: str,
        provider_idempotency_key: str,
    ) -> ExecutionReservation: ...

    async def record_activation_execution_state(
        self,
        *,
        organization_id: str,
        execution_key: str,
        target_state: ExecutionState,
        reason_code: str | None = None,
    ) -> None: ...


class ActivationExecutionLedger:
    """Coordinates a durable execution record with an idempotent external provider call.

    The ledger cannot make an arbitrary remote API transactional.  Therefore the delivery
    adapter must use the returned stable provider idempotency key.  A worker killed after the
    provider accepts the key may retry, but the provider must coalesce that retry; once the
    worker records ``effect_recorded``, subsequent recovery attempts complete the outbox item
    without calling the provider again.
    """

    def __init__(self, repository: ActivationExecutionRepository) -> None:
        self.repository = repository

    @staticmethod
    def _payload(event: OutboxEvent) -> ActivationPayload | None:
        if not event.event_type.startswith("activation."):
            return None
        return validate_activation_payload(event.payload)

    async def begin(self, event: OutboxEvent) -> PolicyDecision:
        payload = self._payload(event)
        if payload is None:
            return PolicyDecision(True, "not_activation_event")
        reservation = await self.repository.begin_activation_execution(
            organization_id=event.organization_id,
            execution_key=payload.execution_key,
            provider_idempotency_key=payload.execution_key,
        )
        if reservation.state == "effect_recorded":
            return PolicyDecision(False, "idempotent_skip")
        if reservation.state == "suppressed":
            return PolicyDecision(False, "suppressed_execution_previously_suppressed")
        if reservation.state == "failed":
            return PolicyDecision(False, "suppressed_execution_previously_failed")
        return PolicyDecision(True, "execution_granted")

    async def record_effect(self, event: OutboxEvent) -> None:
        payload = self._payload(event)
        if payload is not None:
            await self.repository.record_activation_execution_state(
                organization_id=event.organization_id,
                execution_key=payload.execution_key,
                target_state="effect_recorded",
            )

    async def record_suppression(self, event: OutboxEvent, reason_code: str) -> None:
        payload = self._payload(event)
        if payload is not None:
            await self.repository.record_activation_execution_state(
                organization_id=event.organization_id,
                execution_key=payload.execution_key,
                target_state="suppressed",
                reason_code=reason_code,
            )

    async def record_failure(self, event: OutboxEvent, reason_code: str) -> None:
        payload = self._payload(event)
        if payload is not None:
            await self.repository.record_activation_execution_state(
                organization_id=event.organization_id,
                execution_key=payload.execution_key,
                target_state="failed",
                reason_code=reason_code,
            )
