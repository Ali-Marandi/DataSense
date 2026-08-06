# Changelog

All notable changes to DataSense are documented here.
This project follows [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-08-06

### Added
- Five-workspace desktop application (Data, Prepare, Statistics, Visualise, Machine learning).
- Import support for CSV, TSV, delimited text, Excel, JSON, Parquet and SQLite.
- Column quality profiling with KPI overview and virtualised preview of large tables.
- Data preparation: missing-value strategies, deduplication, type conversion, scaling,
  IQR outlier removal, computed columns, query filtering, group-by and pivot tables.
- Labelled undo/redo history for every transformation.
- Statistics: descriptives, correlation matrices, frequency tables, Shapiro-Wilk,
  t-tests, ANOVA, chi-square and OLS regression with interpretation text.
- Ten themed chart types with zoom/pan toolbar and PNG/SVG/PDF export.
- Machine learning: six regressors, five classifiers, K-Means and PCA, trained off the UI thread.
- Styled HTML session reports, `.dsproj` project files and dataset export.
- Dark and light design system, keyboard shortcuts, recent files and status bar.
- PyInstaller build recipe, Inno Setup installer and a GitHub Actions release pipeline.
- Pytest suite covering the data engine, statistics and machine learning modules.
