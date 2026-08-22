"""Ed25519 Trust Exchange primitives for signed, cross-organization Decision Receipts.

This module intentionally contains no key discovery over an untrusted URL.  A caller must
onboard an issuer and provide an :class:`IssuerKeyRegistry` that resolves an issuer/key pair
inside an approved trust relationship.  The reference in-memory registry is for deterministic
tests only; production registries must load public keys and lifecycle state from the Control
Plane database or a trusted key-management integration.
"""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, Mapping, Protocol
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


RECEIPT_SCHEMA = "datasense.decision-receipt/v2"
RECEIPT_TYPE = "datasense-receipt+jws"
RECEIPT_CONTEXT = "datasense:receipt:v1"
EDDSA_ALGORITHM = "EdDSA"
MAX_SERIALIZED_ENVELOPE_BYTES = 32_768
MAX_RECEIPT_LIFETIME = timedelta(minutes=15)
MAX_ISSUED_AT_FUTURE_SKEW = timedelta(seconds=30)


class KeyStatus(StrEnum):
    ACTIVE = "active"
    RETIRING = "retiring"
    REVOKED = "revoked"


@dataclass(frozen=True)
class TrustRelationship:
    """An approved issuer/receiver relationship with a deliberately bounded scope."""

    relationship_id: str
    issuer: str
    receiver_organization_id: str
    environment: str
    allowed_action_types: frozenset[str]
    max_receipt_lifetime: timedelta = MAX_RECEIPT_LIFETIME


@dataclass(frozen=True)
class Ed25519KeyRecord:
    issuer: str
    key_id: str
    public_key: bytes
    status: KeyStatus
    not_before: datetime
    not_after: datetime
    environment: str

    def public_key_object(self) -> Ed25519PublicKey:
        if len(self.public_key) != 32:
            raise ValueError("Ed25519 public key must be exactly 32 bytes")
        return Ed25519PublicKey.from_public_bytes(self.public_key)


@dataclass(frozen=True)
class ExchangeVerification:
    valid: bool
    reason_code: str
    receipt_digest: str | None = None
    action_type: str | None = None
    issuer: str | None = None
    nonce: str | None = None


class IssuerKeyRegistry(Protocol):
    async def relationship(self, *, relationship_id: str) -> TrustRelationship | None: ...

    async def resolve_key(self, *, issuer: str, key_id: str) -> Ed25519KeyRecord | None: ...


class ReceiptReplayStore(Protocol):
    async def add_once(self, namespace: str, value: str, ttl_seconds: int) -> bool: ...


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    if not isinstance(value, str) or not value or len(value) > MAX_SERIALIZED_ENVELOPE_BYTES:
        raise ValueError("invalid base64url member")
    try:
        padding = "=" * (-len(value) % 4)
        return base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except Exception as exc:  # binascii.Error differs by Python version
        raise ValueError("invalid base64url member") from exc


def _parse_canonical_object(value: str) -> dict[str, Any]:
    raw = _b64url_decode(value)
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid canonical json") from exc
    if not isinstance(parsed, dict):
        raise ValueError("signed member must be a JSON object")
    # Reject alternate whitespace/order encodings to make receipt digest reproducible.
    if _canonical_json(parsed) != raw:
        raise ValueError("signed JSON must be canonical")
    return parsed


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _receipt_digest(payload_bytes: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload_bytes).hexdigest()


def _required_payload(payload: Mapping[str, Any]) -> bool:
    expected = {
        "schema", "receipt_id", "issuer", "issuer_tenant", "receiver_organization_id",
        "relationship_id", "issued_at", "expires_at", "action", "outcome",
        "evidence_binding", "policy_digest", "privacy", "nonce",
    }
    return set(payload) == expected


def build_jws_receipt(*, private_key: Ed25519PrivateKey, key_id: str, payload: Mapping[str, Any]) -> dict[str, str]:
    """Create a strict compact JWS-shaped envelope for exchange tests and trusted issuers.

    Private-key bytes never enter the returned mapping.  Production callers should invoke a
    KMS/HSM-backed signing adapter with the same signing-input contract instead of constructing
    an ``Ed25519PrivateKey`` in application memory.
    """
    if not key_id or len(key_id) > 128:
        raise ValueError("key_id is required and bounded")
    header = {
        "alg": EDDSA_ALGORITHM,
        "dsctx": RECEIPT_CONTEXT,
        "kid": key_id,
        "typ": RECEIPT_TYPE,
    }
    protected = _b64url_encode(_canonical_json(header))
    encoded_payload = _b64url_encode(_canonical_json(payload))
    signing_input = f"{protected}.{encoded_payload}".encode("ascii")
    return {
        "protected": protected,
        "payload": encoded_payload,
        "signature": _b64url_encode(private_key.sign(signing_input)),
    }


def public_key_bytes(private_key: Ed25519PrivateKey) -> bytes:
    """Export only the raw public key for test registry construction."""
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


class Ed25519TrustExchangeVerifier:
    """Fail-closed verifier for a bounded Trust Exchange receipt envelope."""

    def __init__(self, registry: IssuerKeyRegistry, replay_store: ReceiptReplayStore) -> None:
        self._registry = registry
        self._replay_store = replay_store

    async def verify(
        self,
        envelope: Mapping[str, Any],
        *,
        receiver_organization_id: str,
        environment: str,
        expected_action_type: str | None = None,
        now: datetime | None = None,
        consume_nonce: bool = True,
    ) -> ExchangeVerification:
        instant = now or datetime.now(timezone.utc)
        try:
            if not isinstance(envelope, Mapping) or set(envelope) != {"protected", "payload", "signature"}:
                return ExchangeVerification(False, "invalid_exchange_envelope")
            raw_size = sum(len(str(value).encode("utf-8")) for value in envelope.values())
            if raw_size > MAX_SERIALIZED_ENVELOPE_BYTES:
                return ExchangeVerification(False, "exchange_envelope_too_large")

            protected = envelope["protected"]
            encoded_payload = envelope["payload"]
            signature = envelope["signature"]
            if not all(isinstance(value, str) for value in (protected, encoded_payload, signature)):
                return ExchangeVerification(False, "invalid_exchange_envelope")
            header = _parse_canonical_object(protected)
            payload = _parse_canonical_object(encoded_payload)
            if set(header) != {"alg", "dsctx", "kid", "typ"}:
                return ExchangeVerification(False, "invalid_exchange_header")
            if header["alg"] != EDDSA_ALGORITHM or header["typ"] != RECEIPT_TYPE or header["dsctx"] != RECEIPT_CONTEXT:
                return ExchangeVerification(False, "unsupported_exchange_algorithm")
            if not isinstance(header["kid"], str) or not header["kid"]:
                return ExchangeVerification(False, "invalid_exchange_key_id")
            if not _required_payload(payload):
                return ExchangeVerification(False, "invalid_exchange_payload")
            if payload["schema"] != RECEIPT_SCHEMA or payload["outcome"] != "allow":
                return ExchangeVerification(False, "unsupported_exchange_receipt")
            if not all(isinstance(payload[key], str) and payload[key] for key in (
                "receipt_id", "issuer", "issuer_tenant", "receiver_organization_id",
                "relationship_id", "policy_digest", "nonce",
            )):
                return ExchangeVerification(False, "invalid_exchange_claim")
            if payload["receiver_organization_id"] != receiver_organization_id:
                return ExchangeVerification(False, "receiver_binding_denied")
            action = payload["action"]
            privacy = payload["privacy"]
            evidence = payload["evidence_binding"]
            if not isinstance(action, dict) or set(action) != {"type", "risk", "purpose_code"}:
                return ExchangeVerification(False, "invalid_exchange_action")
            if not isinstance(privacy, dict) or privacy != {
                "contains_raw_dataset_values": False,
                "contains_local_source_paths": False,
            }:
                return ExchangeVerification(False, "exchange_privacy_contract_denied")
            if not isinstance(evidence, dict) or set(evidence) != {"bundle_sha256", "lineage_sha256"}:
                return ExchangeVerification(False, "invalid_evidence_binding")
            if not all(isinstance(value, str) and value.startswith("sha256:") for value in evidence.values()):
                return ExchangeVerification(False, "invalid_evidence_binding")

            relationship = await self._registry.relationship(relationship_id=payload["relationship_id"])
            if relationship is None:
                return ExchangeVerification(False, "trust_relationship_unknown")
            if relationship.issuer != payload["issuer"] or relationship.receiver_organization_id != receiver_organization_id:
                return ExchangeVerification(False, "trust_relationship_denied")
            if relationship.environment != environment:
                return ExchangeVerification(False, "trust_environment_denied")
            if action["type"] not in relationship.allowed_action_types:
                return ExchangeVerification(False, "trust_action_scope_denied")
            if expected_action_type is not None and action["type"] != expected_action_type:
                return ExchangeVerification(False, "exchange_action_mismatch")

            issued_at = _parse_utc(payload["issued_at"])
            expires_at = _parse_utc(payload["expires_at"])
            if issued_at > instant + MAX_ISSUED_AT_FUTURE_SKEW or expires_at <= instant or expires_at <= issued_at:
                return ExchangeVerification(False, "exchange_receipt_expired")
            if expires_at - issued_at > relationship.max_receipt_lifetime:
                return ExchangeVerification(False, "exchange_receipt_lifetime_denied")

            key = await self._registry.resolve_key(issuer=payload["issuer"], key_id=header["kid"])
            if key is None or key.environment != environment:
                return ExchangeVerification(False, "exchange_key_unknown")
            if key.status == KeyStatus.REVOKED:
                return ExchangeVerification(False, "exchange_key_revoked")
            if key.status not in {KeyStatus.ACTIVE, KeyStatus.RETIRING}:
                return ExchangeVerification(False, "exchange_key_not_active")
            if not (key.not_before <= issued_at <= key.not_after):
                return ExchangeVerification(False, "exchange_key_outside_validity")
            try:
                key.public_key_object().verify(_b64url_decode(signature), f"{protected}.{encoded_payload}".encode("ascii"))
            except InvalidSignature:
                return ExchangeVerification(False, "exchange_signature_invalid")

            payload_bytes = _b64url_decode(encoded_payload)
            digest = _receipt_digest(payload_bytes)
            if consume_nonce:
                nonce_key = hashlib.sha256(
                    f"{relationship.relationship_id}:{payload['nonce']}".encode("utf-8")
                ).hexdigest()
                ttl_seconds = max(1, int((expires_at - instant).total_seconds()))
                if not await self._replay_store.add_once("trust-exchange-receipt", nonce_key, ttl_seconds):
                    return ExchangeVerification(False, "exchange_receipt_replayed", digest, action["type"], payload["issuer"], payload["nonce"])
            return ExchangeVerification(True, "exchange_receipt_valid", digest, action["type"], payload["issuer"], payload["nonce"])
        except (ValueError, TypeError, KeyError):
            return ExchangeVerification(False, "exchange_verification_failed")


class MemoryTrustRegistry:
    """Concurrency-safe deterministic test registry; never use as a production key store."""

    def __init__(self, relationships: list[TrustRelationship], keys: list[Ed25519KeyRecord]) -> None:
        self._relationships = {item.relationship_id: item for item in relationships}
        self._keys = {(item.issuer, item.key_id): item for item in keys}

    async def relationship(self, *, relationship_id: str) -> TrustRelationship | None:
        return self._relationships.get(relationship_id)

    async def resolve_key(self, *, issuer: str, key_id: str) -> Ed25519KeyRecord | None:
        return self._keys.get((issuer, key_id))


class MemoryReplayStore:
    """Test-only one-time nonce store.  Production uses Redis or PostgreSQL with durable TTL."""

    def __init__(self) -> None:
        self._values: set[tuple[str, str]] = set()

    async def add_once(self, namespace: str, value: str, ttl_seconds: int) -> bool:
        if ttl_seconds <= 0:
            return False
        key = (namespace, value)
        if key in self._values:
            return False
        self._values.add(key)
        return True


def new_test_private_key() -> Ed25519PrivateKey:
    """Create a test-only signer. Production key creation belongs in KMS/HSM workflows."""
    return Ed25519PrivateKey.generate()


def valid_test_payload(*, now: datetime, relationship: TrustRelationship) -> dict[str, Any]:
    """Provide synthetic-only claims for deterministic integration tests."""
    issued_at = now.astimezone(timezone.utc).replace(microsecond=0)
    return {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": "00000000-0000-0000-0000-000000000001",
        "issuer": relationship.issuer,
        "issuer_tenant": "issuer-tenant-synthetic",
        "receiver_organization_id": relationship.receiver_organization_id,
        "relationship_id": relationship.relationship_id,
        "issued_at": issued_at.isoformat(),
        "expires_at": (issued_at + timedelta(minutes=5)).isoformat(),
        "action": {"type": next(iter(relationship.allowed_action_types)), "risk": "internal", "purpose_code": "synthetic_test"},
        "outcome": "allow",
        "evidence_binding": {"bundle_sha256": "sha256:" + "a" * 64, "lineage_sha256": "sha256:" + "b" * 64},
        "policy_digest": "sha256:" + "c" * 64,
        "privacy": {"contains_raw_dataset_values": False, "contains_local_source_paths": False},
        "nonce": "synthetic-nonce-0001",
    }
