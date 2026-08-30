"""HTML report generation for analyses, models, charts and governance evidence."""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import html
import io
import json
from dataclasses import dataclass, field

import pandas as pd

from .version import APP_NAME, APP_VERSION

_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin:0; padding:48px 56px; font-family:'Segoe UI',Inter,Arial,sans-serif; background:#f5f7fb; color:#16202f; }
header { border-bottom:3px solid #1f8f8b; padding-bottom:18px; margin-bottom:32px; }
h1 { margin:0; font-size:30px; letter-spacing:-.5px; }
.sub { color:#5b6a80; font-size:14px; margin-top:6px; }
section { background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:24px 26px; margin-bottom:22px; box-shadow:0 6px 18px rgba(20,32,52,.05); }
h2 { margin:0 0 14px; font-size:19px; color:#123; }
p { line-height:1.65; font-size:14px; }
table { border-collapse:collapse; width:100%; font-size:13px; }
th,td { border-bottom:1px solid #eef1f6; padding:8px 10px; text-align:left; }
th { background:#f2f6f9; font-weight:600; }
.metrics { display:flex; flex-wrap:wrap; gap:12px; }
.metric { background:#f2f8f8; border:1px solid #d6eae9; border-radius:10px; padding:12px 16px; min-width:150px; }
.metric span { display:block; font-size:12px; color:#5b6a80; text-transform:uppercase; letter-spacing:.06em; }
.metric strong { font-size:19px; }
.badge { display:inline-block; border-radius:999px; padding:4px 10px; font-size:12px; font-weight:600; background:#eef2f7; }
img { max-width:100%; border-radius:10px; border:1px solid #e2e8f0; }
footer { color:#7b879b; font-size:12px; text-align:center; margin-top:36px; }
"""


@dataclass
class ReportBuilder:
    title: str = "DataSense Analysis Report"
    subtitle: str = ""
    blocks: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def add_text(self, heading: str, body: str) -> None:
        self.blocks.append(f"<section><h2>{html.escape(heading)}</h2><p>{html.escape(body)}</p></section>")

    def add_metrics(self, heading: str, metrics: dict[str, object]) -> None:
        cards = "".join(
            f"<div class='metric'><span>{html.escape(str(k))}</span><strong>{html.escape(str(v))}</strong></div>"
            for k, v in metrics.items()
        )
        self.blocks.append(f"<section><h2>{html.escape(heading)}</h2><div class='metrics'>{cards}</div></section>")

    def add_table(self, heading: str, frame: pd.DataFrame, max_rows: int = 200) -> None:
        table = frame.head(max_rows).to_html(index=False, border=0, na_rep="")
        note = f"<p>Showing the first {max_rows} of {len(frame):,} rows.</p>" if len(frame) > max_rows else ""
        self.blocks.append(f"<section><h2>{html.escape(heading)}</h2>{note}{table}</section>")

    def add_figure(self, heading: str, figure) -> None:
        buffer = io.BytesIO()
        figure.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        self.blocks.append(f"<section><h2>{html.escape(heading)}</h2><img src='data:image/png;base64,{encoded}' alt='{html.escape(heading)}'/></section>")

    def add_plotly_figure(self, heading: str, fig) -> None:
        import plotly.io as pio
        html_div = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
        self.blocks.append(f"<section><h2>{html.escape(heading)}</h2>{html_div}</section>")

    def add_governance_snapshot(self, report=None, gate=None, schema_drift=None) -> None:
        """Add privacy-preserving quality/governance evidence to the report."""
        if report is None:
            self.add_text("Governance", "No quality report was available when this report was generated.")
            return
        metrics = report.summary() if hasattr(report, "summary") else {}
        if gate is not None:
            metrics["Gate decision"] = gate.decision
        if schema_drift is not None:
            metrics["Schema drift"] = schema_drift.decision
        self.add_metrics("Data Quality & Governance", metrics)
        if hasattr(report, "to_frame"):
            self.add_table("Quality Rule Evidence", report.to_frame())

    def add_model_evidence(self, result) -> None:
        """Add a model result while retaining reproducibility metadata but no source rows."""
        if result is None:
            return
        self.add_metrics("Model Evaluation", dict(result.metrics))
        if getattr(result, "table", None) is not None:
            self.add_table("Model Detail", result.table)
        if getattr(result, "note", ""):
            self.add_text("Evaluation Notes", result.note)
        metadata = getattr(result, "metadata", {}) or {}
        if metadata:
            safe_metadata = {key: value for key, value in metadata.items() if key != "model_parameters"}
            self.metadata["model"] = safe_metadata

    def set_metadata(self, **values: object) -> None:
        self.metadata.update(values)

    def render(self) -> str:
        stamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        document_metadata = dict(self.metadata)
        document_metadata.update({"app": APP_NAME, "version": APP_VERSION, "generated_at": stamp})
        metadata_json = html.escape(json.dumps(document_metadata, ensure_ascii=False, default=str, sort_keys=True))
        evidence_fingerprint = hashlib.sha256(metadata_json.encode("utf-8")).hexdigest()
        return (
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<meta name='datasense-evidence-fingerprint' content='{evidence_fingerprint}'>"
            f"<meta name='datasense-metadata' content='{metadata_json}'>"
            f"<title>{html.escape(self.title)}</title><style>{_CSS}</style></head><body>"
            f"<header><h1>{html.escape(self.title)}</h1><div class='sub'>{html.escape(self.subtitle)} &middot; generated {stamp}</div>"
            f"<p><span class='badge'>Evidence {evidence_fingerprint[:12]}</span></p></header>"
            + "".join(self.blocks)
            + f"<footer>{APP_NAME} {APP_VERSION} &middot; evidence fingerprint {evidence_fingerprint}</footer>"
            "</body></html>"
        )

    def save(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.render())
        return path
