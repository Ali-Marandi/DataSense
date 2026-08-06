"""HTML report generation for analyses, models and charts."""
from __future__ import annotations

import base64
import datetime as dt
import html
import io
from dataclasses import dataclass, field

import pandas as pd

from .version import APP_NAME, APP_VERSION

_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin:0; padding:48px 56px; font-family:'Segoe UI',Inter,Arial,sans-serif;
       background:#f5f7fb; color:#16202f; }
header { border-bottom:3px solid #1f8f8b; padding-bottom:18px; margin-bottom:32px; }
h1 { margin:0; font-size:30px; letter-spacing:-.5px; }
.sub { color:#5b6a80; font-size:14px; margin-top:6px; }
section { background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:24px 26px;
          margin-bottom:22px; box-shadow:0 6px 18px rgba(20,32,52,.05); }
h2 { margin:0 0 14px; font-size:19px; color:#123; }
p { line-height:1.65; font-size:14px; }
table { border-collapse:collapse; width:100%; font-size:13px; }
th,td { border-bottom:1px solid #eef1f6; padding:8px 10px; text-align:left; }
th { background:#f2f6f9; font-weight:600; }
.metrics { display:flex; flex-wrap:wrap; gap:12px; }
.metric { background:#f2f8f8; border:1px solid #d6eae9; border-radius:10px; padding:12px 16px;
          min-width:150px; }
.metric span { display:block; font-size:12px; color:#5b6a80; text-transform:uppercase;
               letter-spacing:.06em; }
.metric strong { font-size:19px; }
img { max-width:100%; border-radius:10px; border:1px solid #e2e8f0; }
footer { color:#7b879b; font-size:12px; text-align:center; margin-top:36px; }
"""


@dataclass
class ReportBuilder:
    title: str = "DataSense Analysis Report"
    subtitle: str = ""
    blocks: list[str] = field(default_factory=list)

    def add_text(self, heading: str, body: str) -> None:
        self.blocks.append(
            f"<section><h2>{html.escape(heading)}</h2><p>{html.escape(body)}</p></section>"
        )

    def add_metrics(self, heading: str, metrics: dict[str, object]) -> None:
        cards = "".join(
            f"<div class='metric'><span>{html.escape(str(k))}</span>"
            f"<strong>{html.escape(str(v))}</strong></div>"
            for k, v in metrics.items()
        )
        self.blocks.append(
            f"<section><h2>{html.escape(heading)}</h2><div class='metrics'>{cards}</div></section>"
        )

    def add_table(self, heading: str, frame: pd.DataFrame, max_rows: int = 200) -> None:
        table = frame.head(max_rows).to_html(index=False, border=0, na_rep="")
        note = (
            f"<p>Showing the first {max_rows} of {len(frame):,} rows.</p>"
            if len(frame) > max_rows
            else ""
        )
        self.blocks.append(f"<section><h2>{html.escape(heading)}</h2>{note}{table}</section>")

    def add_figure(self, heading: str, figure) -> None:
        buffer = io.BytesIO()
        figure.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        self.blocks.append(
            f"<section><h2>{html.escape(heading)}</h2>"
            f"<img src='data:image/png;base64,{encoded}' alt='{html.escape(heading)}'/></section>"
        )

    def add_plotly_figure(self, heading: str, fig) -> None:
        """افزودن نمودار تعاملی Plotly به گزارش"""
        import plotly.io as pio
        html_div = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
        self.blocks.append(
            f"<section><h2>{html.escape(heading)}</h2>{html_div}</section>"
        )

    def render(self) -> str:
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        return (
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<title>{html.escape(self.title)}</title><style>{_CSS}</style></head><body>"
            f"<header><h1>{html.escape(self.title)}</h1>"
            f"<div class='sub'>{html.escape(self.subtitle)} &middot; generated {stamp}</div>"
            "</header>" + "".join(self.blocks) +
            f"<footer>{APP_NAME} {APP_VERSION} &middot; automated analysis report</footer>"
            "</body></html>"
        )

    def save(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.render())
        return path
