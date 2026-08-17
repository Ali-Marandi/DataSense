"""Persistent, tenant-scoped circuit breaker primitives for activation delivery.

The repository implementation is responsible for transactionality.  This service deliberately
fails closed when circuit state cannot be read or a transition loses its optimistic-lock race.
No payloads, recipients, or provider responses are accepted as circuit metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    MANUAL_KILL = "manual_kill"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CircuitSnapshot:
    organization_id: str
    scope: str
    state: CircuitState
    version: int
    reason_code: str
    opened_at: datetime | None = None


@dataclass(frozen=True)
class CircuitApproval:
    organization_id: str
    scope: str
    transition: str
    approved_by: str
    approval_reference: str
    approved_at: datetime


class CircuitRepository(Protocol):
    async def get_activation_circuit(self, *, organization_id: str, scope: str) -> CircuitSnapshot | None: ...

    async def compare_and_set_activation_circuit(
        self,
        *,
        organization_id: str,
        scope: str,
        expected_version: int,
        target_state: CircuitState,
        reason_code: str,
        opened_at: datetime | None,
    ) -> CircuitSnapshot | None: ...

    async def record_activation_circuit_approval(self, approval: CircuitApproval) -> None: ...

    async def try_consume_half_open_probe(
        self,
        *,
        organization_id: str,
        scope: str,
        window_started_at: datetime,
        max_attempts: int,
    ) -> bool: ...


class ActivationCircuitService:
    """State machine for activation circuits.

    An absent circuit is ``UNKNOWN`` rather than implicitly closed.  Provisioning must create a
    closed circuit explicitly, which prevents an uninitialised tenant from sending activation
    traffic during a migration or partial rollout.
    """

    def __init__(self, repository: CircuitRepository, *, half_open_max_attempts: int = 5, half_open_window_seconds: int = 60) -> None:
        if half_open_max_attempts < 1 or half_open_window_seconds < 1:
            raise ValueError("half-open limits must be positive")
        self.repository = repository
        self.half_open_max_attempts = half_open_max_attempts
        self.half_open_window_seconds = half_open_window_seconds

    async def state_for(self, *, organization_id: str, scope: str) -> CircuitSnapshot:
        try:
            snapshot = await self.repository.get_activation_circuit(organization_id=organization_id, scope=scope)
        except Exception:
            snapshot = None
        if snapshot is not None:
            return snapshot
        return CircuitSnapshot(organization_id, scope, CircuitState.UNKNOWN, -1, "circuit_state_unavailable")

    async def open(self, *, organization_id: str, scope: str, reason_code: str) -> CircuitSnapshot:
        current = await self.state_for(organization_id=organization_id, scope=scope)
        if current.state in {CircuitState.MANUAL_KILL, CircuitState.UNKNOWN}:
            return current
        if current.state == CircuitState.OPEN:
            return current
        transitioned = await self.repository.compare_and_set_activation_circuit(
            organization_id=organization_id,
            scope=scope,
            expected_version=current.version,
            target_state=CircuitState.OPEN,
            reason_code=reason_code,
            opened_at=datetime.now(timezone.utc),
        )
        return transitioned or await self.state_for(organization_id=organization_id, scope=scope)

    async def enter_half_open(self, *, approval: CircuitApproval) -> CircuitSnapshot:
        if approval.transition != "open_to_half_open":
            raise ValueError("approval must be for open_to_half_open")
        current = await self.state_for(organization_id=approval.organization_id, scope=approval.scope)
        if current.state != CircuitState.OPEN:
            return current
        await self.repository.record_activation_circuit_approval(approval)
        transitioned = await self.repository.compare_and_set_activation_circuit(
            organization_id=approval.organization_id,
            scope=approval.scope,
            expected_version=current.version,
            target_state=CircuitState.HALF_OPEN,
            reason_code="half_open_approved",
            opened_at=current.opened_at,
        )
        return transitioned or await self.state_for(organization_id=approval.organization_id, scope=approval.scope)

    async def close(self, *, approval: CircuitApproval, health_proven: bool) -> CircuitSnapshot:
        if approval.transition != "half_open_to_closed":
            raise ValueError("approval must be for half_open_to_closed")
        current = await self.state_for(organization_id=approval.organization_id, scope=approval.scope)
        if current.state != CircuitState.HALF_OPEN or not health_proven:
            return current
        await self.repository.record_activation_circuit_approval(approval)
        transitioned = await self.repository.compare_and_set_activation_circuit(
            organization_id=approval.organization_id,
            scope=approval.scope,
            expected_version=current.version,
            target_state=CircuitState.CLOSED,
            reason_code="close_approved",
            opened_at=None,
        )
        return transitioned or await self.state_for(organization_id=approval.organization_id, scope=approval.scope)

    async def allow_external_attempt(self, *, organization_id: str, scope: str, now: datetime | None = None) -> tuple[bool, str]:
        """Return a fail-closed, low-cardinality decision for a provider attempt."""
        snapshot = await self.state_for(organization_id=organization_id, scope=scope)
        if snapshot.state == CircuitState.CLOSED:
            return True, "allowed"
        if snapshot.state == CircuitState.HALF_OPEN:
            instant = now or datetime.now(timezone.utc)
            window_started_at = instant.replace(second=0, microsecond=0)
            try:
                allowed = await self.repository.try_consume_half_open_probe(
                    organization_id=organization_id,
                    scope=scope,
                    window_started_at=window_started_at,
                    max_attempts=self.half_open_max_attempts,
                )
            except Exception:
                allowed = False
            return (True, "half_open_probe_allowed") if allowed else (False, "suppressed_half_open_rate_limited")
        if snapshot.state == CircuitState.MANUAL_KILL:
            return False, "suppressed_kill_switch"
        if snapshot.state == CircuitState.OPEN:
            return False, "suppressed_circuit_open"
        return False, "suppressed_circuit_unknown"
