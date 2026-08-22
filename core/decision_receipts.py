"""Proof-carrying, action-scoped decisions built on signed DataSense evidence.

A decision receipt contains no raw dataset values, local paths, recipients, URLs, prompts, or
credentials.  It binds a requested action to a verified evidence bundle and a versioned policy,
then signs that decision for offline verification by another trusted party.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Mapping
from uuid import uuid4

from .evidence import canonical_json, sha256_hex, verify_evidence_bundle

DECISION_RECEIPT_SCHEMA = "datasense.decision-receipt/v1"
SIGNATURE_ALGORITHM = "HMAC-SHA256"
_ACTION_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
_PURPOSE = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")
_POLICY_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

DecisionOutcome = Literal["allow", "approval_required", "block"]
ActionRisk = Literal["internal", "external", "autonomous"]


@dataclass(frozen=True)
class ActionIntent:
    """A deliberately bounded description of the data-derived action being requested."""

    action_type: str
    risk: ActionRisk
    purpose_code: str

    def __post_init__(self) -> None:
        if not _ACTION_TYPE.fullmatch(self.action_type):
            raise ValueError("action_type must be a bounded lowercase identifier")
        if self.risk not in {"internal", "external", "autonomous"}:
            raise ValueError("action risk is invalid")
        if not _PURPOSE.fullmatch(self.purpose_code):
            raise ValueError("purpose_code must be a bounded lowercase identifier")

    def to_dict(self) -> dict[str, str]:
        return {"action_type": self.action_type, "risk": self.risk, "purpose_code": self.purpose_code}


@dataclass(frozen=True)
class DecisionPolicy:
    """Deterministic policy used to evaluate a requested action.

    ``approval_required_risks`` is a safe default rather than an override.  A failed quality
    gate, schema block, invalid evidence signature, or privacy-contract violation always blocks
    the action and cannot be upgraded by an approval.
    """

    version: str = "local-v1"
    max_receipt_ttl_seconds: int = 900
    approval_required_risks: tuple[ActionRisk, ...] = ("external", "autonomous")
    permitted_action_types: tuple[str, ...] = (
        "export.csv",
        "export.xlsx",
        "report.html",
        "dashboard.html",
        "agent.recommendation",
        "agent.external_action",
    )

    def __post_init__(self) -> None:
        if not _POLICY_VERSION.fullmatch(self.version):
            raise ValueError("policy version must be a bounded identifier")
        if not 60 <= self.max_receipt_ttl_seconds <= 86_400:
            raise ValueError("receipt TTL must be between 60 seconds and 24 hours")
        if not self.permitted_action_types or any(not _ACTION_TYPE.fullmatch(item) for item in self.permitted_action_types):
            raise ValueError("permitted action types are invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "max_receipt_ttl_seconds": self.max_receipt_ttl_seconds,
            "approval_required_risks": list(self.approval_required_risks),
            "permitted_action_types": list(self.permitted_action_types),
        }


@dataclass(frozen=True)
class DecisionEvaluation:
    outcome: DecisionOutcome
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class DecisionReceiptVerification:
    valid: bool
    reason: str
    receipt_digest: str | None = None
    outcome: DecisionOutcome | None = None


def _parse_iso_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _stable_evidence_inputs(bundle: Mapping[str, Any]) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    payload = bundle.get("payload")
    if not isinstance(payload, dict):
        return None, ("evidence_payload_missing",)
    privacy = payload.get("privacy")
    if not isinstance(privacy, dict) or any(privacy.get(key) is not False for key in (
        "contains_raw_dataset_values", "contains_rule_parameter_values", "contains_local_source_paths",
    )):
        return None, ("evidence_privacy_contract_invalid",)
    report = payload.get("quality_report")
    drift = payload.get("schema_drift_report")
    lineage = payload.get("lineage")
    if not isinstance(report, dict) or not isinstance(drift, dict) or not isinstance(lineage, dict):
        return None, ("evidence_governance_inputs_missing",)
    gate = report.get("gate_decision")
    if not isinstance(gate, dict):
        return None, ("evidence_gate_decision_missing",)
    gate_decision = gate.get("decision")
    drift_decision = drift.get("decision")
    if not isinstance(gate_decision, str) or not isinstance(drift_decision, str):
        return None, ("evidence_decision_invalid",)
    return {
        "evidence_bundle_sha256": str(bundle.get("payload_sha256", "")),
        "evidence_bundle_schema": str(bundle.get("bundle_schema", "")),
        "quality_gate_decision": gate_decision,
        "schema_drift_decision": drift_decision,
        "lineage_sha256": sha256_hex(lineage),
    }, ()


def evaluate_action(
    evidence_bundle: Mapping[str, Any],
    action: ActionIntent,
    policy: DecisionPolicy,
    key_resolver: Callable[[str], bytes | None],
) -> tuple[DecisionEvaluation, dict[str, Any] | None]:
    """Evaluate an action only after the source evidence signature has been verified."""
    verification = verify_evidence_bundle(evidence_bundle, key_resolver)
    if not verification.valid:
        return DecisionEvaluation("block", ("evidence_signature_invalid",)), None
    inputs, input_errors = _stable_evidence_inputs(evidence_bundle)
    if input_errors:
        return DecisionEvaluation("block", input_errors), None
    assert inputs is not None
    reasons: list[str] = []
    if action.action_type not in policy.permitted_action_types:
        reasons.append("action_type_not_permitted")
    if inputs["quality_gate_decision"] != "approved":
        reasons.append("quality_gate_not_approved")
    if inputs["schema_drift_decision"] == "blocked":
        reasons.append("schema_drift_blocked")
    if reasons:
        return DecisionEvaluation("block", tuple(reasons)), inputs
    if action.risk in policy.approval_required_risks:
        return DecisionEvaluation("approval_required", ("action_risk_requires_approval",)), inputs
    return DecisionEvaluation("allow", ("all_trust_gates_satisfied",)), inputs


def _receipt_payload(
    *,
    evidence_bundle: Mapping[str, Any],
    evidence_inputs: Mapping[str, Any],
    action: ActionIntent,
    policy: DecisionPolicy,
    evaluation: DecisionEvaluation,
    issued_at: datetime,
) -> dict[str, Any]:
    expires_at = issued_at + timedelta(seconds=policy.max_receipt_ttl_seconds)
    return {
        "schema": DECISION_RECEIPT_SCHEMA,
        "receipt_id": str(uuid4()),
        "issued_at": issued_at.replace(microsecond=0).isoformat(),
        "expires_at": expires_at.replace(microsecond=0).isoformat(),
        "privacy": {
            "contains_raw_dataset_values": False,
            "contains_action_recipient": False,
            "contains_local_source_paths": False,
        },
        "action": action.to_dict(),
        "policy": policy.to_dict(),
        "decision": {"outcome": evaluation.outcome, "reason_codes": list(evaluation.reason_codes)},
        "evidence_binding": dict(evidence_inputs),
        # The already-signed, metadata-only evidence bundle makes a receipt portable.  The outer
        # signature binds action, policy, time and decision to that immutable inner bundle.
        "evidence_bundle": json.loads(canonical_json(dict(evidence_bundle)).decode("utf-8")),
    }


def issue_decision_receipt(
    *,
    evidence_bundle: Mapping[str, Any],
    action: ActionIntent,
    policy: DecisionPolicy,
    signing_key: bytes,
    key_id: str,
    evidence_key_resolver: Callable[[str], bytes | None],
    issued_at: datetime | None = None,
) -> dict[str, Any]:
    """Issue a signed receipt for an allow, approval-required, or block decision.

    Block receipts are intentional: they preserve a privacy-safe proof that an unsafe requested
    action was denied.  Callers must permit an action only when the verified outcome is ``allow``.
    """
    if not signing_key:
        raise ValueError("a non-empty receipt signing key is required")
    if not str(key_id).strip():
        raise ValueError("a non-empty receipt key_id is required")
    evaluation, inputs = evaluate_action(evidence_bundle, action, policy, evidence_key_resolver)
    if inputs is None:
        inputs = {
            "evidence_bundle_sha256": str(evidence_bundle.get("payload_sha256", "")),
            "evidence_bundle_schema": str(evidence_bundle.get("bundle_schema", "")),
        }
    now = issued_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("issued_at must be timezone-aware")
    payload = _receipt_payload(
        evidence_bundle=evidence_bundle,
        evidence_inputs=inputs,
        action=action,
        policy=policy,
        evaluation=evaluation,
        issued_at=now.astimezone(timezone.utc),
    )
    digest = sha256_hex(payload)
    signature = hmac.new(signing_key, canonical_json(payload), hashlib.sha256).hexdigest()
    return {
        "receipt_schema": DECISION_RECEIPT_SCHEMA,
        "payload": payload,
        "payload_sha256": digest,
        "signature": {"algorithm": SIGNATURE_ALGORITHM, "key_id": str(key_id).strip(), "value": signature},
    }


def verify_decision_receipt(
    receipt: Mapping[str, Any],
    key_resolver: Callable[[str], bytes | None],
    *,
    expected_action: ActionIntent | None = None,
    now: datetime | None = None,
) -> DecisionReceiptVerification:
    """Verify nested evidence, receipt signature, expiry and optional action binding."""
    if receipt.get("receipt_schema") != DECISION_RECEIPT_SCHEMA:
        return DecisionReceiptVerification(False, "unsupported receipt schema")
    payload = receipt.get("payload")
    signature = receipt.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature, dict):
        return DecisionReceiptVerification(False, "receipt payload or signature is missing")
    digest = sha256_hex(payload)
    if not hmac.compare_digest(str(receipt.get("payload_sha256", "")), digest):
        return DecisionReceiptVerification(False, "receipt digest does not match canonical payload", digest)
    if signature.get("algorithm") != SIGNATURE_ALGORITHM:
        return DecisionReceiptVerification(False, "unsupported receipt signature algorithm", digest)
    key = key_resolver(str(signature.get("key_id", "")))
    if not key:
        return DecisionReceiptVerification(False, "receipt signing key is unavailable", digest)
    expected_signature = hmac.new(key, canonical_json(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(signature.get("value", "")), expected_signature):
        return DecisionReceiptVerification(False, "receipt signature verification failed", digest)
    privacy = payload.get("privacy")
    if not isinstance(privacy, dict) or any(privacy.get(key) is not False for key in (
        "contains_raw_dataset_values", "contains_action_recipient", "contains_local_source_paths",
    )):
        return DecisionReceiptVerification(False, "receipt privacy contract is invalid", digest)
    evidence_bundle = payload.get("evidence_bundle")
    if not isinstance(evidence_bundle, dict):
        return DecisionReceiptVerification(False, "bound evidence bundle is missing", digest)
    evidence_verification = verify_evidence_bundle(evidence_bundle, key_resolver)
    if not evidence_verification.valid:
        return DecisionReceiptVerification(False, "bound evidence bundle is invalid", digest)
    binding = payload.get("evidence_binding")
    if not isinstance(binding, dict) or not hmac.compare_digest(
        str(binding.get("evidence_bundle_sha256", "")), str(evidence_bundle.get("payload_sha256", ""))
    ):
        return DecisionReceiptVerification(False, "evidence binding does not match bundle", digest)
    expires_at = _parse_iso_timestamp(payload.get("expires_at"))
    instant = now or datetime.now(timezone.utc)
    if expires_at is None or instant.astimezone(timezone.utc) > expires_at.astimezone(timezone.utc):
        return DecisionReceiptVerification(False, "receipt has expired or has an invalid expiry", digest)
    action = payload.get("action")
    if not isinstance(action, dict):
        return DecisionReceiptVerification(False, "receipt action is missing", digest)
    if expected_action is not None and action != expected_action.to_dict():
        return DecisionReceiptVerification(False, "receipt is not valid for the requested action", digest)
    decision = payload.get("decision")
    outcome = decision.get("outcome") if isinstance(decision, dict) else None
    if outcome not in {"allow", "approval_required", "block"}:
        return DecisionReceiptVerification(False, "receipt decision is invalid", digest)
    return DecisionReceiptVerification(True, "receipt and bound evidence are valid", digest, outcome)


def write_decision_receipt(path: str | Path, receipt: Mapping[str, Any]) -> None:
    """Write a receipt as canonicalized, human-readable JSON without retaining a signing key."""
    Path(path).write_text(json.dumps(dict(receipt), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def read_decision_receipt(path: str | Path) -> dict[str, Any]:
    """Read a receipt and reject non-object roots before verification."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("decision receipt root must be a JSON object")
    return value


def action_is_authorized(
    receipt: Mapping[str, Any],
    key_resolver: Callable[[str], bytes | None],
    action: ActionIntent,
    *,
    now: datetime | None = None,
) -> bool:
    """Return true only for a valid, unexpired, action-matched allow receipt."""
    verification = verify_decision_receipt(receipt, key_resolver, expected_action=action, now=now)
    return verification.valid and verification.outcome == "allow"
