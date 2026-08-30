# DataSense Comprehensive Development Master Plan — 2026

## Executive objective

Evolve DataSense from a strong Windows analytics desktop application into a trusted, extensible analytics platform with a coherent product surface across data preparation, statistics, machine learning, finance/risk, governance, reporting, automation, security, and software supply-chain integrity.

## Current strengths observed

- Windows desktop product with a coherent Qt-based UI and bundled release workflow.
- Broad import/export support and a central `DataManager` with undo/redo history.
- Data Contracts, Quality Gates, schema drift controls, lineage, evidence, and signed local receipts.
- Existing ML, statistics, dashboard, database, SQL, streaming, AutoML, AI assistant, and reporting surfaces.
- Finance layer already expanding toward beta, factors, volatility and VaR analytics.
- Existing GitHub Actions coverage for regression, packaging, Kubernetes rendering, and governance validation.

## Product pillars

### 1. Data foundation

Goals:
- Make every transformation reproducible, inspectable, and reversible.
- Add dataset fingerprints, semantic schema profiles, freshness/volume anomaly detection, and explicit null/duplicate/outlier policies.
- Introduce sampling-aware profiling for very large datasets so previews and summaries stay responsive.
- Add safe database access patterns with parameterized identifiers and connection diagnostics.

Acceptance criteria:
- No mutation silently invalidates prior quality evidence without clearing its validity.
- Every export can report source, transformation count, schema fingerprint, quality status, and evidence status.
- Large-file profiling avoids unnecessary full copies.

### 2. Statistical analysis

Goals:
- Add effect sizes and confidence intervals alongside p-values.
- Add multiple-comparison corrections and assumption diagnostics.
- Add robust statistics and bootstrap confidence intervals where computationally practical.
- Make interpretations explicit about association versus causation.

Acceptance criteria:
- Every inferential result exposes sample size and method assumptions.
- P-values never appear without effect-size/context fields in exported evidence.

### 3. Machine learning

Goals:
- Standardize train/validation/test semantics.
- Add leakage checks, stratified/time-aware splits, baseline models, calibration, feature importance, and model comparison tables.
- Store model metadata and reproducibility fingerprints.
- Harden persisted-model loading with explicit trust boundaries.

Acceptance criteria:
- Time-series datasets cannot accidentally use random shuffling in time-sensitive workflows.
- Model reports include dataset fingerprint, feature list, split policy, metric set, and runtime versions.

### 4. Finance and risk

Goals:
- Consolidate CAPM, factor models, volatility, VaR, Expected Shortfall, drawdown, Sharpe/Sortino, beta, and rolling diagnostics.
- Add VaR backtesting and exception counts.
- Add portfolio aggregation with explicit weighting and alignment rules.
- Keep all financial analytics clearly labeled as analysis/decision support, not investment advice.

Acceptance criteria:
- Risk functions are deterministic given the same inputs and parameters.
- Tail-risk outputs state horizon, confidence, observation count, and methodology.
- Backtests distinguish model diagnostics from forward guarantees.

### 5. Governance and trust

Goals:
- Expand Data Contracts beyond single-column checks to cross-column and dataset-level assertions.
- Add contract versioning and approval metadata.
- Add evidence freshness/version matching across data, report, model, and export artifacts.
- Add explicit stale-report blocking when the working dataframe changes.

Priority cross-column rules:
- `less_than_or_equal`
- `greater_than_or_equal`
- `equal`
- `conditional_required`
- `date_order`
- `sum_to`
- `unique_combination`

Acceptance criteria:
- Cross-column rules retain only aggregate diagnostics, never raw sensitive values.
- Invalid rule configuration becomes `error`, never a false pass.

### 6. Reporting and decision support

Goals:
- Produce one canonical evidence model for HTML/PDF/JSON exports.
- Add an executive summary that surfaces data quality, drift, model risk, and key findings.
- Add reproducibility metadata and report fingerprints.
- Support reusable report templates with safe, deterministic rendering.

Acceptance criteria:
- Report and evidence outputs can be matched by fingerprint.
- A report cannot claim validation/certification unless an explicit evidence policy allows it.

### 7. UX and accessibility

Goals:
- Consolidate repeated UI patterns into reusable widgets.
- Add consistent loading, empty, error, warning, and success states.
- Improve keyboard navigation, focus visibility, accessible labels, and dense-table ergonomics.
- Localize user-facing vocabulary without localizing machine-readable identifiers.

Acceptance criteria:
- No destructive/irreversible operation happens without an explicit confirmation or policy gate.
- Long-running analysis never freezes the main window.

### 8. Performance

Goals:
- Profile startup, import, preview, statistics, chart rendering, ML training, and report generation.
- Move heavyweight work to worker threads/processes where safe.
- Cache immutable derived artifacts using dataset/parameter fingerprints.
- Avoid redundant dataframe copies.

Acceptance criteria:
- Performance regressions become measurable CI smoke metrics, not subjective impressions.

### 9. Security and privacy

Goals:
- Keep sensitive-data scanning local and metadata-only.
- Minimize network-capable dependencies and clearly isolate optional cloud features.
- Add dependency review, secret scanning policy, and release provenance attestation.
- Never log API keys, tokens, dataset values, or full user-provided queries when sensitive.

Acceptance criteria:
- Security-sensitive paths fail closed on invalid configuration.
- Release artifacts have verifiable provenance.

### 10. Engineering and delivery

Goals:
- Use a protected integration branch and small reviewable feature branches.
- Make tests the primary contract for core behavior.
- Keep release builds reproducible and provenance-linked.
- Add changelog/release-note discipline and migration notes for serialized project formats.

## Release sequencing

### Phase A — Foundation

- Finance/risk core stabilization.
- Cross-column governance contracts.
- Export/evidence consistency.
- Dependency review and release attestations.
- Security and performance baseline.

### Phase B — Intelligence

- Leakage-aware ML evaluation.
- Statistical effect sizes/confidence intervals.
- Risk backtesting.
- Advanced drift detection.
- Dataset-level anomaly detection.

### Phase C — Product

- Executive analytics workspace.
- Reusable report templates.
- Workflow automation primitives.
- Saved analysis recipes and reproducible runs.

### Phase D — Enterprise

- Signed evidence bundles.
- Policy-driven approvals.
- Team/workspace separation.
- Centralized catalog integration.
- Controlled connectors.

## Non-goals / safeguards

- No automatic external trading, medical diagnosis, or safety-critical action.
- No silent data mutation to improve a score.
- No claim that a statistical association is causal.
- No claim that provenance proves software safety by itself.

## Definition of done

A feature is complete only when its core behavior, failure modes, serialization impact, UI exposure (when applicable), test coverage, documentation, and release/security implications have been considered.
