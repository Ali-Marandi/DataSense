"""Strict metadata-only activation payload firewall.

Activation events cannot carry a recipient address, free-form message, dataset value, URL, file
path, or command output.  Every identifier below is an opaque SHA-256/HMAC reference, allowing
operations and idempotency without introducing customer data into the outbox or observability.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from .metrics import ACTIVATION_PAYLOAD_REJECTIONS

_HEX_64 = re.compile(r"^[a-f0-9]{64}$")
_SCOPE = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
_REQUIRED = frozenset({
    "version", "case_id", "scope", "channel", "recipient_ref", "execution_key",
    "policy_allowed", "recipient_verified", "trigger_version", "policy_version", "correlation_id",
})


class ActivationPayloadError(ValueError):
    """Validation error exposing only a bounded reason code."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class ActivationPayload:
    version: int
    case_id: str
    scope: str
    channel: str
    recipient_ref: str
    execution_key: str
    policy_allowed: bool
    recipient_verified: bool
    trigger_version: int
    policy_version: int
    correlation_id: str

    @classmethod
    def parse(cls, payload: dict[str, object]) -> "ActivationPayload":
        unknown = set(payload) - _REQUIRED
        missing = _REQUIRED - set(payload)
        if unknown:
            raise ActivationPayloadError("unknown_field")
        if missing:
            raise ActivationPayloadError("missing_required_field")
        if payload["version"] != 1:
            raise ActivationPayloadError("unsupported_version")
        for key in ("case_id", "recipient_ref", "execution_key"):
            value = payload[key]
            if not isinstance(value, str) or not _HEX_64.fullmatch(value):
                raise ActivationPayloadError("invalid_opaque_reference")
        scope = payload["scope"]
        if not isinstance(scope, str) or not _SCOPE.fullmatch(scope):
            raise ActivationPayloadError("invalid_scope")
        channel = payload["channel"]
        if channel not in {"in_app", "external"}:
            raise ActivationPayloadError("invalid_channel")
        for key in ("policy_allowed", "recipient_verified"):
            if type(payload[key]) is not bool:
                raise ActivationPayloadError("invalid_boolean")
        for key in ("trigger_version", "policy_version"):
            value = payload[key]
            if type(value) is not int or value < 1 or value > 1_000_000:
                raise ActivationPayloadError("invalid_version_reference")
        correlation_id = payload["correlation_id"]
        if not isinstance(correlation_id, str):
            raise ActivationPayloadError("invalid_correlation_id")
        try:
            UUID(correlation_id)
        except ValueError as exc:
            raise ActivationPayloadError("invalid_correlation_id") from exc
        return cls(
            version=1,
            case_id=str(payload["case_id"]),
            scope=scope,
            channel=str(channel),
            recipient_ref=str(payload["recipient_ref"]),
            execution_key=str(payload["execution_key"]),
            policy_allowed=bool(payload["policy_allowed"]),
            recipient_verified=bool(payload["recipient_verified"]),
            trigger_version=int(payload["trigger_version"]),
            policy_version=int(payload["policy_version"]),
            correlation_id=correlation_id,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "case_id": self.case_id,
            "scope": self.scope,
            "channel": self.channel,
            "recipient_ref": self.recipient_ref,
            "execution_key": self.execution_key,
            "policy_allowed": self.policy_allowed,
            "recipient_verified": self.recipient_verified,
            "trigger_version": self.trigger_version,
            "policy_version": self.policy_version,
            "correlation_id": self.correlation_id,
        }


def validate_activation_payload(payload: dict[str, object]) -> ActivationPayload:
    """Validate and increment a bounded rejection metric without recording payload content."""
    try:
        return ActivationPayload.parse(payload)
    except ActivationPayloadError as exc:
        ACTIVATION_PAYLOAD_REJECTIONS.labels(reason_code=exc.reason_code).inc()
        raise
