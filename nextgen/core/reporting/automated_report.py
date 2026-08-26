from __future__ import annotations

import hashlib
import html
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping
from uuid import uuid4

from core.analysis.contracts import ProcessingResult
from core.data.model import DatasetProfile
from core.governance.contracts import QualityReport


@dataclass(frozen=True)
class AutomatedReportConfig:
    """Non-sensitive presentation and retention controls for local report generation."""

    title: str = "DataSense automated readiness report"
    include_quality_evidence: bool = True
    max_column_summaries: int = 50

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Automated report title cannot be empty.")
        if not 1 <= self.max_column_summaries <= 500:
            raise ValueError("max_column_summaries must be in the interval [1, 500].")


@dataclass(frozen=True)
class AutomatedReportArtifact:
    """References to an atomically created report and its metadata-only manifest."""

    report_id: str
    artifact_path: Path
    manifest_path: Path
    sha256: str
    created_at: str
    readiness_score: int
    quality_status: str


class AutomatedReportService:
    """Builds an aggregate-only, local HTML report from existing domain results.

    This layer intentionally does not receive a DataFrame. It can only use a
    ``DatasetProfile``, a ``ProcessingResult`` and optional quality evidence. This
    boundary prevents raw cells, source paths and unapproved calculations from leaking
    into an automated artifact. Both the report and companion manifest are committed
    with atomic replacement to avoid partially-written output after an interruption.
    """

    schema = "datasense.automated-report-manifest/v1"

    def __init__(
        self,
        config: AutomatedReportConfig | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
        report_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.config = config or AutomatedReportConfig()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._report_id_factory = report_id_factory or (lambda: str(uuid4()))

    def generate(
        self,
        destination: str | Path,
        *,
        profile: DatasetProfile,
        readiness: ProcessingResult,
        quality: QualityReport | None = None,
    ) -> AutomatedReportArtifact:
        """Create report and manifest from aggregate-only domain inputs.

        ``readiness`` must be emitted by ``data-readiness-insights/v1`` and must match
        the supplied profile's row/column count. The return value contains no raw data.
        """
        self._validate_inputs(profile=profile, readiness=readiness, quality=quality)
        artifact_path = self._normalize_destination(destination)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        created_at = self._utc_timestamp()
        report_id = self._report_id_factory()
        quality_status = self._quality_status(quality)
        document = self._html_document(
            profile=profile,
            readiness=readiness,
            quality=quality,
            report_id=report_id,
            created_at=created_at,
        )
        self._atomic_write_text(artifact_path, document)
        sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        manifest_path = artifact_path.with_suffix(artifact_path.suffix + ".manifest.json")
        manifest = self._manifest(
            report_id=report_id,
            created_at=created_at,
            artifact_path=artifact_path,
            sha256=sha256,
            profile=profile,
            readiness=readiness,
            quality_status=quality_status,
        )
        self._atomic_write_json(manifest_path, manifest)
        return AutomatedReportArtifact(
            report_id=report_id,
            artifact_path=artifact_path,
            manifest_path=manifest_path,
            sha256=sha256,
            created_at=created_at,
            readiness_score=int(readiness.summary["readiness_score"]),
            quality_status=quality_status,
        )

    def _validate_inputs(
        self,
        *,
        profile: DatasetProfile,
        readiness: ProcessingResult,
        quality: QualityReport | None,
    ) -> None:
        if not isinstance(profile, DatasetProfile):
            raise TypeError("Automated reporting expects a DatasetProfile.")
        if not isinstance(readiness, ProcessingResult):
            raise TypeError("Automated reporting expects a ProcessingResult.")
        if readiness.module_id != "data-readiness-insights/v1":
            raise ValueError("Automated reporting requires data-readiness-insights/v1 output.")
        required = {"rows", "columns", "readiness_score", "ready"}
        if not required.issubset(readiness.summary):
            raise ValueError("Readiness result does not provide the required aggregate metrics.")
        if readiness.summary["rows"] != profile.rows or readiness.summary["columns"] != profile.columns:
            raise ValueError("Dataset profile does not match the readiness result.")
        score = readiness.summary["readiness_score"]
        if not isinstance(score, int) or not 0 <= score <= 100:
            raise ValueError("Readiness score must be an integer in the interval [0, 100].")
        if quality is not None and not isinstance(quality, QualityReport):
            raise TypeError("Quality evidence must be a QualityReport or None.")

    @staticmethod
    def _normalize_destination(destination: str | Path) -> Path:
        path = Path(destination).expanduser()
        return path if path.suffix.lower() in {".html", ".htm"} else path.with_suffix(".html")

    def _utc_timestamp(self) -> str:
        instant = self._clock()
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=timezone.utc)
        return instant.astimezone(timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def _quality_status(quality: QualityReport | None) -> str:
        return "not_run" if quality is None else str(quality.summary()["status"])

    def _manifest(
        self,
        *,
        report_id: str,
        created_at: str,
        artifact_path: Path,
        sha256: str,
        profile: DatasetProfile,
        readiness: ProcessingResult,
        quality_status: str,
    ) -> dict[str, object]:
        return {
            "schema": self.schema,
            "report_id": report_id,
            "created_at": created_at,
            "artifact": {"file_name": artifact_path.name, "sha256": sha256, "media_type": "text/html"},
            "dataset": {"rows": profile.rows, "columns": profile.columns, "memory_mb": round(profile.memory_mb, 4)},
            "readiness": {
                "module_id": readiness.module_id,
                "score": readiness.summary["readiness_score"],
                "ready": readiness.summary["ready"],
                "warning_count": len(readiness.warnings),
            },
            "quality": {"status": quality_status},
            "privacy": {"contains_raw_dataset_values": False, "contains_local_source_paths": False},
        }

    def _html_document(
        self,
        *,
        profile: DatasetProfile,
        readiness: ProcessingResult,
        quality: QualityReport | None,
        report_id: str,
        created_at: str,
    ) -> str:
        score = int(readiness.summary["readiness_score"])
        status = "READY" if bool(readiness.summary["ready"]) else "REVIEW REQUIRED"
        quality_status = self._quality_status(quality)
        dataset_rows = self._metric_rows(profile.summary())
        readiness_rows = self._metric_rows(self._safe_readiness_summary(readiness.summary))
        warning_rows = self._warning_rows(readiness.warnings)
        quality_rows = self._quality_rows(quality)
        columns_rows = self._column_rows(profile)
        title = html.escape(self.config.title)
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>
:root{{color-scheme:light;--ink:#122033;--muted:#5b6a7e;--line:#d7e0ea;--surface:#f6f8fb;--accent:#087ea4;--ok:#087b61;--warn:#a15c00}}
body{{font-family:Segoe UI,Arial,sans-serif;max-width:1060px;margin:42px auto;padding:0 22px;color:var(--ink);background:var(--surface)}}
h1{{font-size:30px;margin:0 0 6px}}h2{{font-size:18px;margin:0 0 14px}}.meta{{color:var(--muted);font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}.panel{{background:#fff;border:1px solid var(--line);padding:20px;margin:16px 0}}
.status{{display:inline-block;font-weight:700;padding:7px 10px;border:1px solid currentColor}}.ready{{color:var(--ok)}}.review{{color:var(--warn)}}
table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{text-align:left;padding:9px 4px;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--muted);font-weight:600}}
ul{{margin:0;padding-left:20px}}code{{word-break:break-all}}.note{{font-size:13px;color:var(--muted)}}
</style></head><body>
<h1>{title}</h1><p class="meta">Report ID: <code>{html.escape(report_id)}</code> · Generated: {html.escape(created_at)}</p>
<div class="panel"><span class="status {'ready' if status == 'READY' else 'review'}">{status} · {score}/100</span>
<p class="note">This local report contains aggregate profile, readiness, and quality metadata only. It contains no raw dataset values or local source paths.</p></div>
<div class="grid"><section class="panel"><h2>Dataset profile</h2><table>{dataset_rows}</table></section><section class="panel"><h2>Readiness metrics</h2><table>{readiness_rows}</table></section></div>
<section class="panel"><h2>Readiness warnings</h2>{warning_rows}</section>
<section class="panel"><h2>Quality evidence · {html.escape(quality_status)}</h2><table>{quality_rows}</table></section>
<section class="panel"><h2>Column profile</h2><table><thead><tr><th>Column</th><th>Type</th><th>Missing</th><th>Unique</th></tr></thead><tbody>{columns_rows}</tbody></table></section>
</body></html>"""

    @staticmethod
    def _metric_rows(values: Mapping[str, object]) -> str:
        return "".join(
            f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
            for key, value in values.items()
        )

    @staticmethod
    def _safe_readiness_summary(summary: Mapping[str, object]) -> dict[str, object]:
        allowlist = (
            "readiness_score",
            "ready",
            "rows",
            "columns",
            "columns_with_missing",
            "missing_cells",
            "missing_cell_ratio",
            "high_cardinality_columns",
            "non_finite_numeric_cells",
            "outlier_cells",
        )
        return {key: summary[key] for key in allowlist if key in summary}

    @staticmethod
    def _warning_rows(warnings: tuple[str, ...]) -> str:
        if not warnings:
            return "<p class=\"note\">No aggregate readiness warnings were detected.</p>"
        return "<ul>" + "".join(f"<li>{html.escape(warning)}</li>" for warning in warnings) + "</ul>"

    def _quality_rows(self, quality: QualityReport | None) -> str:
        if quality is None:
            return "<tr><td colspan=\"4\" class=\"note\">No quality check was supplied.</td></tr>"
        if not self.config.include_quality_evidence:
            return "<tr><td colspan=\"4\" class=\"note\">Quality evidence omitted by report configuration.</td></tr>"
        rows = []
        for result in quality.results:
            rows.append(
                "<tr>"
                f"<td>{html.escape(result.rule.column)}</td>"
                f"<td>{html.escape(result.rule.rule_type)}</td>"
                f"<td>{html.escape(result.rule.severity)}</td>"
                f"<td>{html.escape('PASS' if result.passed else 'FAIL')} · {result.violations}</td>"
                "</tr>"
            )
        return "".join(rows) or "<tr><td colspan=\"4\" class=\"note\">No quality rules configured.</td></tr>"

    def _column_rows(self, profile: DatasetProfile) -> str:
        rows = []
        for column in profile.column_summaries[: self.config.max_column_summaries]:
            rows.append(
                "<tr>"
                f"<td>{html.escape(column.name)}</td>"
                f"<td>{html.escape(column.dtype)}</td>"
                f"<td>{column.missing}</td><td>{column.unique}</td>"
                "</tr>"
            )
        if len(profile.column_summaries) > self.config.max_column_summaries:
            rows.append(
                f"<tr><td colspan=\"4\" class=\"note\">Showing first {self.config.max_column_summaries} aggregate column summaries.</td></tr>"
            )
        return "".join(rows)

    @staticmethod
    def _atomic_write_text(path: Path, content: str) -> None:
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temporary_path = Path(handle.name)
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def _atomic_write_json(self, path: Path, value: dict[str, object]) -> None:
        self._atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
