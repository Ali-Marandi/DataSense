"""Signed, replay-safe internal alert receiver for one-way circuit opening."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from .activation_circuit import ActivationCircuitService, CircuitSnapshot
from .ephemeral_store import EphemeralStore
from .metrics import ACTIVATION_ALERTS

_NONCE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_SCOPE = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
_REQUIRED = frozenset({"alert_name", "environment", "organization_id", "scope", "timestamp", "nonce"})


class AlertVerificationError(ValueError):
    def __init__(self, status_code: int, reason_code: str) -> None:
        super().__init__(reason_code)
        self.status_code = status_code
        self.reason_code = reason_code


@dataclass(frozen=True)
class VerifiedActivationAlert:
    alert_name: str
    organization_id: str
    scope: str
    timestamp: int
    nonce: str


class ActivationAlertController:
    """Accept only authenticated, fresh and unique alerts that can open a circuit.

    This receiver is intentionally one-way: it never closes a circuit, changes a rollout, or
    invokes a provider.  The request signature covers a canonical JSON representation, avoiding
    whitespace and key-order ambiguity while keeping verification independent of web framework
    serialisation behaviour.
    """

    def __init__(
        self,
        *,
        hmac_key: str,
        nonce_store: EphemeralStore,
        circuit: ActivationCircuitService,
        environment: str,
        allowed_alert_names: frozenset[str] = frozenset({"activation_outbox_lag_critical"}),
        max_clock_skew_seconds: int = 300,
    ) -> None:
        if not hmac_key:
            raise ValueError("alert HMAC key must not be empty")
        if max_clock_skew_seconds < 30 or max_clock_skew_seconds > 900:
            raise ValueError("alert clock-skew window must be between 30 and 900 seconds")
        self._hmac_key = hmac_key.encode("utf-8")
        self._nonce_store = nonce_store
        self._circuit = circuit
        self._environment = environment
        self._allowed_alert_names = allowed_alert_names
        self._max_clock_skew_seconds = max_clock_skew_seconds

    @staticmethod
    def canonical_body(payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

    @classmethod
    def signature_for(cls, hmac_key: str, payload: dict[str, Any]) -> str:
        return "sha256=" + hmac.new(hmac_key.encode("utf-8"), cls.canonical_body(payload), hashlib.sha256).hexdigest()

    @staticmethod
    def _parse(raw_body: bytes) -> dict[str, Any]:
        try:
            value = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AlertVerificationError(401, "invalid_alert_body") from exc
        if not isinstance(value, dict) or set(value) != _REQUIRED:
            raise AlertVerificationError(401, "invalid_alert_shape")
        return value

    def _verify_signature(self, payload: dict[str, Any], signature: str | None) -> None:
        expected = self.signature_for(self._hmac_key.decode("utf-8"), payload)
        if not signature or not hmac.compare_digest(expected, signature):
            raise AlertVerificationError(401, "invalid_alert_signature")

    def _validate_payload(self, payload: dict[str, Any], now: datetime) -> VerifiedActivationAlert:
        alert_name = payload["alert_name"]
        environment = payload["environment"]
        organization_id = payload["organization_id"]
        scope = payload["scope"]
        timestamp = payload["timestamp"]
        nonce = payload["nonce"]
        if not isinstance(alert_name, str) or alert_name not in self._allowed_alert_names:
            raise AlertVerificationError(403, "alert_not_allowlisted")
        if environment != self._environment:
            raise AlertVerificationError(403, "alert_environment_denied")
        if not isinstance(organization_id, str):
            raise AlertVerificationError(401, "invalid_alert_organization")
        try:
            UUID(organization_id)
        except ValueError as exc:
            raise AlertVerificationError(401, "invalid_alert_organization") from exc
        if not isinstance(scope, str) or not _SCOPE.fullmatch(scope):
            raise AlertVerificationError(401, "invalid_alert_scope")
        if type(timestamp) is not int or abs(int(now.timestamp()) - timestamp) > self._max_clock_skew_seconds:
            raise AlertVerificationError(401, "stale_alert")
        if not isinstance(nonce, str) or not _NONCE.fullmatch(nonce):
            raise AlertVerificationError(401, "invalid_alert_nonce")
        return VerifiedActivationAlert(alert_name, organization_id, scope, timestamp, nonce)

    async def receive(self, *, raw_body: bytes, signature: str | None, now: datetime | None = None) -> CircuitSnapshot:
        instant = now or datetime.now(timezone.utc)
        try:
            payload = self._parse(raw_body)
            self._verify_signature(payload, signature)
            alert = self._validate_payload(payload, instant)
            nonce_key = hashlib.sha256(alert.nonce.encode("utf-8")).hexdigest()
            accepted = await self._nonce_store.add_once(
                "activation-controller-alert", nonce_key, self._max_clock_skew_seconds
            )
            if not accepted:
                raise AlertVerificationError(409, "replayed_alert")
            snapshot = await self._circuit.open(
                organization_id=alert.organization_id,
                scope=alert.scope,
                reason_code="outbox_lag_critical",
            )
            if snapshot.state.value not in {"open", "manual_kill"}:
                raise AlertVerificationError(503, "circuit_state_unavailable")
        except AlertVerificationError as exc:
            ACTIVATION_ALERTS.labels(outcome=exc.reason_code).inc()
            raise
        except Exception as exc:
            ACTIVATION_ALERTS.labels(outcome="controller_dependency_unavailable").inc()
            raise AlertVerificationError(503, "controller_dependency_unavailable") from exc
        ACTIVATION_ALERTS.labels(outcome="accepted").inc()
        return snapshot
