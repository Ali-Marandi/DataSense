"""Interactive HTML dashboard builder (Plotly) — shareable, no server needed."""
from __future__ import annotations

import datetime as dt
import html

import numpy as np
import pandas as pd

from .insights import health_score, insights_frame, summary_metrics
from .version import APP_NAME, APP_VERSION

_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
:root{{--bg:#0d1420;--card:#141d2c;--line:#22304a;--txt:#e8eef7;--mut:#93a3ba;--acc:#22c1a4;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--txt);font-family:'Segoe UI',Inter,Arial,sans-serif}}
header{{padding:32px 40px 20px;border-bottom:1px solid var(--line)}}
h1{{margin:0;font-size:26px;letter-spacing:-.4px}}
.sub{{color:var(--mut);font-size:13px;margin-top:6px}}
main{{padding:28px 40px 60px;display:grid;gap:20px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px}}
.kpi span{{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut)}}
.kpi strong{{font-size:22px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px 22px}}
.card h2{{margin:0 0 14px;font-size:17px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:20px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left}}
th{{color:var(--mut);font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:.06em}}
.badge{{padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}}
.critical{{background:#4a1d24;color:#ff9aa6}}.warning{{background:#4a3a1a;color:#ffd08a}}
.info{{background:#12343a;color:#7fe3d1}}
footer{{color:var(--mut);font-size:12px;text-align:center;padding:20px}}
</style></head><body>
<header><h1>{title}</h1><div class="sub">{subtitle} &middot; generated {generated}</div></header>
<main>{body}</main>
<footer>{app} {version} &middot; interactive dashboard</footer>
</body></html>"""


def _kpis(metrics: dict[str, str]) -> str:
    cells = "".join(
        f'<div class="kpi"><span>{html.escape(k)}</span><strong>{html.escape(str(v))}</strong></div>'
        for k, v in metrics.items()
    )
    return f'<section class="kpis">{cells}</section>'


def _plot(div_id: str, traces: list[dict], layout: dict) -> str:
    import json

    layout = {
        "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": "#e8eef7"}, "margin": {"t": 30, "r": 20, "b": 40, "l": 50},
        "height": 320, **layout,
    }
    return (
        f'<div id="{div_id}"></div>'
        f"<script>Plotly.newPlot('{div_id}',{json.dumps(traces)},{json.dumps(layout)},"
        f"{{responsive:true,displaylogo:false}});</script>"
    )


def _table(frame: pd.DataFrame, severity_column: str | None = None) -> str:
    if frame is None or frame.empty:
        return '<p class="sub">Nothing to show.</p>'
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in frame.columns)
    rows = []
    for _, row in frame.iterrows():
        cells = []
        for col in frame.columns:
            value = html.escape(str(row[col]))
            if severity_column and col == severity_column:
                value = f'<span class="badge {html.escape(str(row[col]))}">{value}</span>'
            cells.append(f"<td>{value}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def build_dashboard(
    df: pd.DataFrame, path: str, title: str | None = None, subtitle: str = "",
    max_charts: int = 6,
) -> tuple[bool, str]:
    """Render an interactive, self-contained HTML dashboard for a dataset."""
    if df is None or df.empty:
        return False, "No dataset to visualise."
    title = title or f"{APP_NAME} dashboard"
    blocks: list[str] = [_kpis(summary_metrics(df))]

    numeric = df.select_dtypes(include=np.number)
    charts: list[str] = []
    idx = 0

    score = health_score(df)
    charts.append(
        '<div class="card"><h2>Dataset health</h2>'
        + _plot(
            "gauge",
            [{
                "type": "indicator", "mode": "gauge+number", "value": score,
                "gauge": {
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#22c1a4"},
                    "steps": [
                        {"range": [0, 50], "color": "#3a1c22"},
                        {"range": [50, 80], "color": "#3b3218"},
                        {"range": [80, 100], "color": "#12343a"},
                    ],
                },
            }],
            {"height": 280},
        )
        + "</div>"
    )

    for col in numeric.columns[:max_charts]:
        series = numeric[col].dropna()
        if series.empty:
            continue
        idx += 1
        charts.append(
            f'<div class="card"><h2>Distribution of {html.escape(str(col))}</h2>'
            + _plot(
                f"hist{idx}",
                [{"type": "histogram", "x": series.head(20000).tolist(),
                  "marker": {"color": "#22c1a4"}, "nbinsx": 40}],
                {"xaxis": {"title": str(col)}},
            )
            + "</div>"
        )

    for col in df.select_dtypes(exclude=[np.number, "datetime64[ns]"]).columns[:3]:
        counts = df[col].astype(str).value_counts().head(12)
        if counts.empty:
            continue
        idx += 1
        charts.append(
            f'<div class="card"><h2>Top values in {html.escape(str(col))}</h2>'
            + _plot(
                f"bar{idx}",
                [{"type": "bar", "x": counts.index.tolist(), "y": counts.values.tolist(),
                  "marker": {"color": "#4f9dff"}}],
                {},
            )
            + "</div>"
        )

    if numeric.shape[1] >= 2:
        corr = numeric.corr(numeric_only=True).round(3)
        charts.append(
            '<div class="card"><h2>Correlation matrix</h2>'
            + _plot(
                "heat",
                [{"type": "heatmap", "z": corr.values.tolist(),
                  "x": [str(c) for c in corr.columns], "y": [str(c) for c in corr.index],
                  "colorscale": "Teal", "zmin": -1, "zmax": 1}],
                {"height": 380},
            )
            + "</div>"
        )

    blocks.append(f'<section class="grid">{"".join(charts)}</section>')
    blocks.append(
        '<section class="card"><h2>Automatic insights</h2>'
        + _table(insights_frame(df), severity_column="severity")
        + "</section>"
    )
    blocks.append(
        '<section class="card"><h2>Data sample</h2>'
        + _table(df.head(20).astype(str))
        + "</section>"
    )

    document = _TEMPLATE.format(
        title=html.escape(title),
        subtitle=html.escape(subtitle or "interactive analytics"),
        generated=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        body="".join(blocks),
        app=APP_NAME,
        version=APP_VERSION,
    )
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(document)
    except Exception as exc:
        return False, str(exc)
    return True, f"Dashboard exported to {path}"
