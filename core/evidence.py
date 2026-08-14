"""Privacy-safe signed evidence bundles for DataSense Trust Center.

Bundles intentionally contain governance metadata, hashes and rule outcomes only. Raw
cells, rule parameter values and local source paths are excluded so a bundle can be
shared for review without becoming a copy of the underlying dataset.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .governance import (
    DataContract,
    QualityGatePolicy,
    QualityHistory,
    QualityReport,
    SchemaDriftPolicy,
    SchemaDriftReport,
    SchemaSnapshot,
)
from .lineage import LineageTrail

EVIDENCE_BUNDLE_SCHEMA = "datasense.evidence-bundle/v1"
SIGNATURE_ALGORITHM = "HMAC-SHA256"


def canonical_json(value: Mapping[str, Any]) -> bytes:
    """Encode a mapping deterministically for signing and digest calculation."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def sha256_hex(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _parameter_fingerprint(params: Mapping[str, Any]) -> str:
    return sha256_hex(dict(params))


def _safe_contract(contract: DataContract) -> dict[str, Any]:
    return {
        "name": contract.name,
        "rule_count": len(contract.rules),
        "rules": [
            {
                "name": rule.display_name(),
                "rule_type": rule.rule_type,
                "column": rule.column,
                "severity": rule.severity,
                "parameter_fingerprint": _parameter_fingerprint(rule.params),
            }
            for rule in contract.rules
        ],
    }


def _safe_report(report: QualityReport, policy: QualityGatePolicy) -> dict[str, Any]:
    decision = report.gate_decision(policy)
    return {
        "contract_name": report.contract_name,
        "generated_at": report.generated_at,
        "rows": report.rows,
        "status": report.status,
        "score": report.score,
        "summary": report.summary(),
        "gate_decision": decision.to_dict(),
        "results": [
            {
                "rule_name": result.rule.display_name(),
                "rule_type": result.rule.rule_type,
                "column": result.rule.column,
                "severity": result.rule.severity,
                "parameter_fingerprint": _parameter_fingerprint(result.rule.params),
                "status": result.status,
                "violations": result.violations,
            }
            for result in report.results
        ],
    }


def _safe_lineage(lineage: LineageTrail) -> dict[str, Any]:
    """Retain transformation provenance but never local source paths or cell values."""
    return {
        "summary": lineage.summary(),
        "events": [
            {
                "sequence": event.sequence,
                "operation": event.operation,
                "occurred_at": event.occurred_at,
                "input_rows": event.input_rows,
                "output_rows": event.output_rows,
                "input_fingerprint": event.input_fingerprint,
                "output_fingerprint": event.output_fingerprint,
                "added_columns": list(event.added_columns),
                "removed_columns": list(event.removed_columns),
                "dtype_changes": list(event.dtype_changes),
            }
            for event in lineage.events
        ],
    }


def build_evidence_payload(
    *,
    report: QualityReport,
    contract: DataContract,
    gate_policy: QualityGatePolicy,
    quality_history: QualityHistory,
    schema_baseline: SchemaSnapshot | None,
    schema_drift_policy: SchemaDriftPolicy,
    schema_drift_report: SchemaDriftReport,
    lineage: LineageTrail,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic, metadata-only evidence payload before signing."""
    created = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "schema": EVIDENCE_BUNDLE_SCHEMA,
        "generated_at": created,
        "privacy": {
            "contains_raw_dataset_values": False,
            "contains_rule_parameter_values": False,
            "contains_local_source_paths": False,
        },
        "contract": _safe_contract(contract),
        "quality_report": _safe_report(report, gate_policy),
        "quality_history": quality_history.to_dict(),
        "schema_baseline": schema_baseline.to_dict() if schema_baseline else None,
        "schema_drift_policy": schema_drift_policy.to_dict(),
        "schema_drift_report": schema_drift_report.to_dict(),
        "lineage": _safe_lineage(lineage),
    }


@dataclass(frozen=True)
class EvidenceVerification:
    valid: bool
    reason: str
    payload_digest: str | None = None


def sign_evidence_payload(payload: Mapping[str, Any], signing_key: bytes, key_id: str) -> dict[str, Any]:
    """Return a portable signed bundle without embedding the secret key."""
    if not signing_key:
        raise ValueError("A non-empty signing key is required.")
    clean_key_id = str(key_id).strip()
    if not clean_key_id:
        raise ValueError("A non-empty key_id is required.")
    immutable_payload = json.loads(canonical_json(dict(payload)).decode("utf-8"))
    digest = sha256_hex(immutable_payload)
    signature = hmac.new(signing_key, canonical_json(immutable_payload), hashlib.sha256).hexdigest()
    return {
        "bundle_schema": EVIDENCE_BUNDLE_SCHEMA,
        "payload": immutable_payload,
        "payload_sha256": digest,
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "key_id": clean_key_id,
            "value": signature,
        },
    }


def verify_evidence_bundle(
    bundle: Mapping[str, Any], key_resolver: Callable[[str], bytes | None],
) -> EvidenceVerification:
    """Verify schema, canonical digest and HMAC without mutating the bundle."""
    if bundle.get("bundle_schema") != EVIDENCE_BUNDLE_SCHEMA:
        return EvidenceVerification(False, "Unsupported evidence bundle schema.")
    payload = bundle.get("payload")
    signature = bundle.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature, dict):
        return EvidenceVerification(False, "Bundle payload or signature is missing.")
    digest = sha256_hex(payload)
    if not hmac.compare_digest(str(bundle.get("payload_sha256", "")), digest):
        return EvidenceVerification(False, "Payload digest does not match canonical payload.", digest)
    if signature.get("algorithm") != SIGNATURE_ALGORITHM:
        return EvidenceVerification(False, "Unsupported signature algorithm.", digest)
    key_id = str(signature.get("key_id", ""))
    key = key_resolver(key_id)
    if not key:
        return EvidenceVerification(False, f"No signing key is available for key_id '{key_id}'.", digest)
    expected = hmac.new(key, canonical_json(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(signature.get("value", "")), expected):
        return EvidenceVerification(False, "Signature verification failed; the bundle may have been modified.", digest)
    return EvidenceVerification(True, "Signature and canonical payload are valid.", digest)


def read_signing_key(path: str | Path) -> bytes:
    """Read a local HMAC secret; callers must keep the file out of source control."""
    value = Path(path).read_bytes().strip()
    if not value:
        raise ValueError("The signing key file is empty.")
    return value


def write_evidence_bundle(path: str | Path, bundle: Mapping[str, Any]) -> None:
    Path(path).write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def read_evidence_bundle(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Evidence bundle root must be a JSON object.")
    return value


def _main() -> int:
    parser = argparse.ArgumentParser(description="Verify a DataSense signed evidence bundle.")
    parser.add_argument("bundle", help="Path to a signed evidence JSON bundle")
    parser.add_argument("--key-file", required=True, help="Path to the HMAC signing key file")
    parser.add_argument("--key-id", help="Expected key id; verifies the bundle uses this key id")
    args = parser.parse_args()
    bundle = read_evidence_bundle(args.bundle)
    key = read_signing_key(args.key_file)
    expected_key_id = args.key_id or Path(args.key_file).stem

    def resolver(key_id: str) -> bytes | None:
        return key if hmac.compare_digest(key_id, expected_key_id) else None

    result = verify_evidence_bundle(bundle, resolver)
    print(json.dumps({"valid": result.valid, "reason": result.reason, "payload_sha256": result.payload_digest}, ensure_ascii=False))
    return 0 if result.valid else 1


if __name__ == "__main__":  # pragma: no cover - exercised through the CLI entrypoint
    raise SystemExit(_main())
