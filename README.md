<p align="center">
  <img src="assets/icon.png" width="112" alt="DataSense logo">
</p>

<h1 align="center">DataSense</h1>

<p align="center">
  <b>Advanced data analysis, modelling and visualisation studio for Windows.</b><br>
  Import your data, clean it, test it, model it, chart it and export evidence-aware reports — without writing code.
</p>

---

## Current product capabilities

DataSense is local-first: dataset rows stay local unless the user explicitly opts into a remote AI request. Governance outputs are evidence metadata, not a claim of causal or scientific validity. The roadmap is maintained in [`docs/ROADMAP.md`](docs/ROADMAP.md).

### Data and preparation
- Import CSV, TSV, delimited text, Excel, JSON, Parquet, Avro and SQLite.
- Memory-aware loading with numeric downcasting and categorical compression; large delimited files use chunked reads.
- Profile columns, missingness, uniqueness and numeric distribution; apply deterministic transformations with undo/redo and lineage.
- Save and restore `.dsproj` projects, including governance configuration and quality history.

### Statistics and finance
- Descriptive statistics, correlations, normality tests, Welch/paired t-tests, ANOVA, chi-square and OLS.
- Inferential outputs include effect sizes, confidence intervals and multiple-testing controls.
- Portfolio volatility, Sharpe/Sortino, drawdown, VaR/expected shortfall and aligned weighted portfolio returns.

### Machine learning
- Regression, classification, K-Means and PCA with worker-thread training.
- Fixed seeds, time-aware splits, leakage warnings, baseline comparison and reproducibility metadata.
- Prediction outputs retain row-alignment metadata so append-back operations cannot silently reorder results.
- `.dsmodel` artifacts carry model metadata; the local Model Registry adds versioning, lifecycle state and artifact SHA-256 integrity records.

### Trust and governance
- Local sensitive-data detection without retaining observed values.
- Data contracts, schema-drift policies, quality gates, bounded quality history and signed metadata-only evidence bundles.
- Mutations invalidate prior quality results so stale evidence cannot be reused as current validation.
- Security operations are copy-on-write and fail closed on invalid decryption.

### Reporting and AI
- Styled HTML reports with governance snapshots, model evidence, application version and evidence fingerprint.
- PDF reporting and interactive Plotly dashboards.
- AI assistant defaults to local metadata-only answers. Remote OpenAI usage requires explicit opt-in and `OPENAI_API_KEY`; raw dataset rows are never sent implicitly.

### Enterprise controls
- Database connector defaults to read-only `SELECT`/`WITH` access and uses SQLAlchemy `URL.create` so credentials are not interpolated into connection URLs.
- Dependency/security quality gates, Windows release provenance, signed local evidence and Kubernetes baseline validation are wired into CI.
- A bounded, thread-safe LRU cache is available for expensive analytical computations.

## Run from source

```bash
git clone https://github.com/Ali-Marandi/DataSense.git
cd DataSense
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Tests

```bash
pip install -r enterprise_control_plane/requirements.txt
pytest -q
```

## License

MIT
