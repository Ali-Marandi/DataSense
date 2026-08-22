"""Race-safe Automatic Rollback reference coordinator for the Action Gate.

The coordinator is intentionally narrow: a verified trigger may only move a rollout towards a
safer state.  It never closes a circuit, grants a new permit, deletes audit history, or attempts
to compensate an unknown provider effect.  The memory repository provides deterministic race
tests; production must implement the same single-transaction contract with PostgreSQL row locks,
version predicates, and a unique trigger-evidence index.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol

from .trust_exchange import Ed25519TrustExchangeVerifier, ExchangeVerification


class RolloutMode(StrEnum):
    SHADOW = "shadow"
    LIMITED_ENFORCE = "limited_enforce"
    ENFORCE = "enforce"
    ROLLBACK_ACTIVE = "rollback_active"
    MANUAL_KILL = "manual_kill"


class ExecutionMode(StrEnum):
    OBSERVE_ONLY = "observe_only"
    ALLOW_GUARDED = "allow_guarded"
    SUPPRESS_EXTERNAL = "suppress_external"


class RollbackOutcome(StrEnum):
    ROLLBACK_ACTIVE = "rollback_active"
    ALREADY_HANDLED = "already_handled"
    ALREADY_CONTAINED = "already_contained"
    STATE_UNKNOWN = "suppressed_rollout_state_unknown"
    TRIGGER_DENIED = "suppressed_trigger_denied"
    CIRCUIT_PENDING = "rollback_active_circuit_pending"


@dataclass(frozen=True)
class RolloutState:
    organization_id: str
    scope: str
    mode: RolloutMode
    execution_mode: ExecutionMode
    active_policy_digest: str
    last_known_good_policy_digest: str
    version: int
    gate_epoch: int


@dataclass(frozen=True)
class RollbackTrigger:
    organization_id: str
    scope: str
    trigger_type: str
    reason_code: str
    evidence_digest: str
    observed_at: datetime

    def validate(self) -> None:
        if not self.organization_id or not self.scope or not self.trigger_type or not self.reason_code:
            raise ValueError("rollback trigger fields are required")
        if not self.evidence_digest.startswith("sha256:") or len(self.evidence_digest) != 71:
            raise ValueError("rollback trigger requires a sha256 evidence digest")
        if self.observed_at.tzinfo is None:
            raise ValueError("rollback trigger observed_at must be timezone-aware")


@dataclass(frozen=True)
class ActionPermit:
    organization_id: str
    scope: str
    execution_key: str
    receipt_digest: str
    gate_epoch: int
    expires_at: datetime


@dataclass(frozen=True)
class RollbackActivation:
    outcome: RollbackOutcome
    rollback_id: str | None
    state: RolloutState | None


class RollbackRepository(Protocol):
    async def activate_rollback_once(self, trigger: RollbackTrigger) -> RollbackActivation: ...

    async def issue_permit(
        self,
        *,
        organization_id: str,
        scope: str,
        execution_key: str,
        receipt_digest: str,
        expires_at: datetime,
    ) -> ActionPermit | None: ...

    async def consume_permit_once(self, permit: ActionPermit, *, now: datetime) -> bool: ...


class CircuitOpenOutbox(Protocol):
    async def enqueue_open(self, *, organization_id: str, scope: str, reason_code: str, rollback_id: str) -> None: ...


class CASRollbackCoordinator:
    """Coordinates a durable safe-state transition and an eventually delivered circuit open."""

    def __init__(
        self,
        repository: RollbackRepository,
        *,
        circuit_outbox: CircuitOpenOutbox | None = None,
        exchange_verifier: Ed25519TrustExchangeVerifier | None = None,
    ) -> None:
        self._repository = repository
        self._circuit_outbox = circuit_outbox
        self._exchange_verifier = exchange_verifier

    async def activate(self, trigger: RollbackTrigger) -> RollbackActivation:
        """Apply a deduplicated one-way safety transition.

        The repository transition is authoritative and must be atomic.  Circuit signalling is
        intentionally after commit: an outbox delay cannot re-open Action Gate permissions.
        """
        trigger.validate()
        activation = await self._repository.activate_rollback_once(trigger)
        if activation.outcome != RollbackOutcome.ROLLBACK_ACTIVE or activation.rollback_id is None:
            return activation
        if self._circuit_outbox is None:
            return activation
        try:
            await self._circuit_outbox.enqueue_open(
                organization_id=trigger.organization_id,
                scope=trigger.scope,
                reason_code=trigger.reason_code,
                rollback_id=activation.rollback_id,
            )
            return activation
        except Exception:
            # State is already suppress_external.  A durable delivery worker may retry the
            # outbox notification; never reverse the state or return an unsafe "allow".
            return RollbackActivation(RollbackOutcome.CIRCUIT_PENDING, activation.rollback_id, activation.state)

    async def activate_from_exchange_receipt(
        self,
        envelope: dict[str, str],
        *,
        organization_id: str,
        scope: str,
        receiver_organization_id: str,
        environment: str,
        now: datetime | None = None,
    ) -> RollbackActivation:
        """Accept only a valid Ed25519 receipt scoped to ``rollback.trigger``.

        The exchange receipt acts as authenticated, replay-protected trigger evidence.  Its
        receiver identity must be the local Control Plane organization; the untrusted envelope
        never supplies the target organization or rollback scope.
        """
        if self._exchange_verifier is None:
            return RollbackActivation(RollbackOutcome.TRIGGER_DENIED, None, None)
        verification: ExchangeVerification = await self._exchange_verifier.verify(
            envelope,
            receiver_organization_id=receiver_organization_id,
            environment=environment,
            expected_action_type="rollback.trigger",
            now=now,
            consume_nonce=True,
        )
        if not verification.valid or not verification.receipt_digest:
            return RollbackActivation(RollbackOutcome.TRIGGER_DENIED, None, None)
        instant = now or datetime.now(timezone.utc)
        return await self.activate(RollbackTrigger(
            organization_id=organization_id,
            scope=scope,
            trigger_type="trust_exchange_signed_trigger",
            reason_code="verified_exchange_rollback_trigger",
            evidence_digest=verification.receipt_digest,
            observed_at=instant,
        ))

    async def reserve_permit(
        self,
        *,
        organization_id: str,
        scope: str,
        execution_key: str,
        receipt_digest: str,
        expires_at: datetime,
    ) -> ActionPermit | None:
        """Reserve a single-use permit while the gate is currently allow-guarded."""
        return await self._repository.issue_permit(
            organization_id=organization_id,
            scope=scope,
            execution_key=execution_key,
            receipt_digest=receipt_digest,
            expires_at=expires_at,
        )

    async def commit_permit(self, permit: ActionPermit, *, now: datetime | None = None) -> bool:
        """Consume a permit only if its fencing epoch remains current after a rollback race."""
        return await self._repository.consume_permit_once(permit, now=now or datetime.now(timezone.utc))


class MemoryRollbackRepository:
    """Test reference for the SQL CAS contract; protected by one transaction-like async lock."""

    def __init__(self, states: list[RolloutState]) -> None:
        self._states = {(state.organization_id, state.scope): state for state in states}
        self._triggers: dict[tuple[str, str, str], RollbackActivation] = {}
        self._permits: dict[tuple[str, str], ActionPermit] = {}
        self._consumed_permits: set[tuple[str, str]] = set()
        self._lock = asyncio.Lock()
        self.activation_count = 0

    async def activate_rollback_once(self, trigger: RollbackTrigger) -> RollbackActivation:
        key = (trigger.organization_id, trigger.scope, trigger.evidence_digest)
        state_key = (trigger.organization_id, trigger.scope)
        async with self._lock:
            duplicate = self._triggers.get(key)
            if duplicate is not None:
                return RollbackActivation(RollbackOutcome.ALREADY_HANDLED, duplicate.rollback_id, duplicate.state)
            current = self._states.get(state_key)
            if current is None:
                result = RollbackActivation(RollbackOutcome.STATE_UNKNOWN, None, None)
                self._triggers[key] = result
                return result
            if current.mode == RolloutMode.MANUAL_KILL or current.execution_mode == ExecutionMode.SUPPRESS_EXTERNAL:
                result = RollbackActivation(RollbackOutcome.ALREADY_CONTAINED, None, current)
                self._triggers[key] = result
                return result
            if current.mode not in {RolloutMode.SHADOW, RolloutMode.LIMITED_ENFORCE, RolloutMode.ENFORCE}:
                result = RollbackActivation(RollbackOutcome.STATE_UNKNOWN, None, current)
                self._triggers[key] = result
                return result
            target = RolloutState(
                organization_id=current.organization_id,
                scope=current.scope,
                mode=RolloutMode.ROLLBACK_ACTIVE,
                execution_mode=ExecutionMode.SUPPRESS_EXTERNAL,
                active_policy_digest=current.last_known_good_policy_digest,
                last_known_good_policy_digest=current.last_known_good_policy_digest,
                version=current.version + 1,
                gate_epoch=current.gate_epoch + 1,
            )
            self._states[state_key] = target
            self.activation_count += 1
            result = RollbackActivation(
                RollbackOutcome.ROLLBACK_ACTIVE,
                f"rollback-{self.activation_count}",
                target,
            )
            self._triggers[key] = result
            return result

    async def issue_permit(
        self,
        *,
        organization_id: str,
        scope: str,
        execution_key: str,
        receipt_digest: str,
        expires_at: datetime,
    ) -> ActionPermit | None:
        if expires_at.tzinfo is None or not execution_key or not receipt_digest.startswith("sha256:"):
            return None
        state_key = (organization_id, scope)
        permit_key = (organization_id, execution_key)
        async with self._lock:
            state = self._states.get(state_key)
            if state is None or state.execution_mode != ExecutionMode.ALLOW_GUARDED:
                return None
            if permit_key in self._permits or permit_key in self._consumed_permits:
                return None
            permit = ActionPermit(organization_id, scope, execution_key, receipt_digest, state.gate_epoch, expires_at)
            self._permits[permit_key] = permit
            return permit

    async def consume_permit_once(self, permit: ActionPermit, *, now: datetime) -> bool:
        permit_key = (permit.organization_id, permit.execution_key)
        state_key = (permit.organization_id, permit.scope)
        async with self._lock:
            existing = self._permits.get(permit_key)
            state = self._states.get(state_key)
            if existing != permit or state is None:
                return False
            if now.tzinfo is None or now >= permit.expires_at:
                return False
            if state.execution_mode != ExecutionMode.ALLOW_GUARDED or state.gate_epoch != permit.gate_epoch:
                return False
            if permit_key in self._consumed_permits:
                return False
            self._consumed_permits.add(permit_key)
            return True

    async def state_for(self, organization_id: str, scope: str) -> RolloutState | None:
        async with self._lock:
            return self._states.get((organization_id, scope))


class RecordingCircuitOutbox:
    """Synthetic test double for durable circuit-open message emission."""

    def __init__(self, *, should_fail: bool = False) -> None:
        self.calls: list[tuple[str, str, str, str]] = []
        self.should_fail = should_fail

    async def enqueue_open(self, *, organization_id: str, scope: str, reason_code: str, rollback_id: str) -> None:
        if self.should_fail:
            raise RuntimeError("synthetic outbox unavailable")
        self.calls.append((organization_id, scope, reason_code, rollback_id))
