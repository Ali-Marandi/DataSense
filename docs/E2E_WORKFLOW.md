# DataSense End-to-End Workflow

The supported reviewable workflow is:

1. Import a dataset locally.
2. Profile and prepare it through `DataManager` transformations.
3. Capture supported preparation operations as an `AnalysisRecipe`.
4. Evaluate quality contracts and schema drift.
5. Run statistics, finance or ML/AutoML analysis.
6. Persist model artifacts and register their metadata when applicable.
7. Build metadata-only evidence and sign it when a trusted export is required.
8. Export an HTML/PDF report or dashboard.
9. Save the project as `.dsproj` and restore it later.
10. Replay approved recipe steps only through the explicit allowlist.

## Invariants

- Raw dataset values are not included in evidence bundles.
- Recipe execution cannot execute arbitrary Python code.
- Dataset mutations invalidate the active governance result.
- Model approval is blocked when the artifact checksum does not match its registry record.
- ML predictions carry row-alignment metadata when the evaluated sample is a subset of the source dataset.
- Database access defaults to read-only query semantics.
