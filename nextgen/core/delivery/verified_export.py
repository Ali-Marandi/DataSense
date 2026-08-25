from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from core.data.model import DatasetProfile
from core.delivery.signing import SigningKeyProvider
from core.governance.contracts import QualityReport


@dataclass(frozen=True)
class ExportDecision:
    approved: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class VerifiedExportResult:
    decision: ExportDecision
    artifact_path: Path | None
    receipt_path: Path
    receipt_sha256: str


class VerifiedExportService:
    """Creates an HTML artifact and a signed metadata-only companion receipt.

    Raw DataFrame values are intentionally not interpolated into either the report or
    receipt.  The report uses aggregate profile data, while its receipt can be verified
    through the injected signing provider.
    """

    def decide(self, report: QualityReport | None) -> ExportDecision:
        if report is None:
            return ExportDecision(False, ("quality_check_missing",))
        if not report.approved:
            return ExportDecision(False, ("quality_gate_blocked",))
        return ExportDecision(True, ("all_trust_gates_satisfied",))

    def export_html(
        self,
        path: str | Path,
        frame: pd.DataFrame,
        profile: DatasetProfile,
        quality: QualityReport | None,
        signing_provider: SigningKeyProvider,
        policy_version: str = "desktop-alpha-v1",
    ) -> VerifiedExportResult:
        self._validate_export_inputs(frame, profile)
        destination = self._normalized_html_destination(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        decision = self.decide(quality)
        receipt_path = destination.with_suffix(destination.suffix + ".trust-receipt.json")
        receipt = self._receipt(decision, profile, quality, signing_provider, policy_version)
        self._atomic_write_json(receipt_path, receipt)
        receipt_sha256 = hashlib.sha256(receipt_path.read_bytes()).hexdigest()

        if not decision.approved:
            return VerifiedExportResult(decision, None, receipt_path, receipt_sha256)

        self._atomic_write_text(destination, self._html_document(profile, quality, receipt_sha256))
        return VerifiedExportResult(decision, destination, receipt_path, receipt_sha256)

    def verify_receipt(self, receipt_path: str | Path, signing_provider: SigningKeyProvider) -> bool:
        raw_receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
        required = {"payload", "payload_sha256", "signature_base64", "algorithm", "key_id"}
        if not required.issubset(raw_receipt):
            return False
        if raw_receipt["algorithm"] != signing_provider.algorithm or raw_receipt["key_id"] != signing_provider.key_id:
            return False
        encoded_payload = self._canonical_payload(raw_receipt["payload"])
        if hashlib.sha256(encoded_payload).hexdigest() != raw_receipt["payload_sha256"]:
            return False
        try:
            signature = base64.b64decode(raw_receipt["signature_base64"], validate=True)
        except (ValueError, TypeError):
            return False
        return signing_provider.verify(encoded_payload, signature)

    @staticmethod
    def _normalized_html_destination(path: str | Path) -> Path:
        destination = Path(path).expanduser()
        if destination.suffix.lower() not in {".html", ".htm"}:
            destination = destination.with_suffix(".html")
        return destination

    @staticmethod
    def _validate_export_inputs(frame: pd.DataFrame, profile: DatasetProfile) -> None:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("Verified export expects a pandas DataFrame.")
        if len(frame) != profile.rows or frame.shape[1] != profile.columns:
            raise ValueError("Dataset profile does not match the export DataFrame.")

    def _receipt(
        self,
        decision: ExportDecision,
        profile: DatasetProfile,
        quality: QualityReport | None,
        signing_provider: SigningKeyProvider,
        policy_version: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "datasense.verified-export-receipt/v2",
            "receipt_id": str(uuid4()),
            "issued_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "policy_version": policy_version,
            "decision": {"outcome": "allow" if decision.approved else "block", "reason_codes": list(decision.reason_codes)},
            "dataset": {"rows": profile.rows, "columns": profile.columns, "memory_mb": round(profile.memory_mb, 4)},
            "quality": quality.summary() if quality else None,
            "privacy": {"contains_raw_dataset_values": False, "contains_local_source_paths": False},
        }
        encoded_payload = self._canonical_payload(payload)
        signature = signing_provider.sign(encoded_payload)
        return {
            "payload": payload,
            "payload_sha256": hashlib.sha256(encoded_payload).hexdigest(),
            "signature_base64": base64.b64encode(signature).decode("ascii"),
            "algorithm": signing_provider.algorithm,
            "key_id": signing_provider.key_id,
        }

    @staticmethod
    def _canonical_payload(payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _atomic_write_text(path: Path, content: str) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)

    def _atomic_write_json(self, path: Path, value: dict[str, Any]) -> None:
        self._atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))

    @staticmethod
    def _html_document(profile: DatasetProfile, quality: QualityReport | None, receipt_sha256: str) -> str:
        quality_summary = quality.summary() if quality else {"status": "not_run", "rules": 0, "failed_rules": 0}
        metric_items = "".join(
            f"<li><span>{key}</span><strong>{value}</strong></li>" for key, value in profile.summary().items()
        )
        outcome_class = "approved" if quality_summary["status"] == "approved" else "blocked"
        return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>DataSense verified report</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;max-width:880px;margin:48px auto;color:#18212f;background:#f6f8fc;padding:0 18px}}
.card{{background:#fff;border:1px solid #dce3ee;border-radius:12px;padding:24px;margin:16px 0;box-shadow:0 2px 10px #22304d12}}
.status{{font-weight:700;padding:8px 12px;border-radius:999px;display:inline-block}}.approved{{color:#056656;background:#def7ed}}.blocked{{color:#a42525;background:#fee8e8}}
ul{{list-style:none;padding:0}}li{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #edf1f7}}li span{{color:#52617a}}
code{{word-break:break-all;color:#52617a}}
</style></head><body>
<h1>DataSense verified report</h1>
<div class=\"card\"><span class=\"status {outcome_class}\">Quality status: {quality_summary['status']}</span>
<p>This report contains aggregate metrics only. Its companion trust receipt records the decision evidence without raw dataset values.</p></div>
<div class=\"card\"><h2>Dataset summary</h2><ul>{metric_items}</ul></div>
<div class=\"card\"><h2>Decision evidence</h2><p>Rules evaluated: {quality_summary['rules']}; failed rules: {quality_summary['failed_rules']}.</p><p>Receipt SHA-256: <code>{receipt_sha256}</code></p></div>
</body></html>"""
