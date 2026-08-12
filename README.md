<p align="center">
  <img src="assets/icon.png" width="112" alt="DataSense logo">
</p>

<h1 align="center">DataSense</h1>

<p align="center">
  <b>Advanced data analysis, modelling and visualisation studio for Windows.</b><br>
  Import your data, clean it, test it, model it, chart it and export a report — without writing code.
</p>

<p align="center">
  <a href="https://github.com/Ali-Marandi/DataSense/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/Ali-Marandi/DataSense?color=0f9488"></a>
  <a href="https://github.com/Ali-Marandi/DataSense/actions/workflows/release.yml"><img alt="Build" src="https://github.com/Ali-Marandi/DataSense/actions/workflows/release.yml/badge.svg"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

---

## Download

Grab the latest Windows build from the [Releases page](https://github.com/Ali-Marandi/DataSense/releases/latest):

| File | Description |
| --- | --- |
| `DataSense-<version>-setup.exe` | Installer with Start-menu and desktop shortcuts plus an uninstaller (recommended) |
| `DataSense-<version>-windows-x64-portable.zip` | Portable build — unzip and run `DataSense.exe` |

Windows 10/11 64-bit. Python is **not** required — everything is bundled.

## Feature tour

### Data workspace
- Import **CSV, TSV, delimited text, Excel, JSON, Parquet and SQLite**.
- KPI header: rows, columns, numeric columns, missing cells, duplicate rows, memory footprint.
- Virtualised preview that stays responsive on large tables.
- **Column quality profile**: dtype, non-null and missing counts, missing %, uniqueness, mean/std/min/max.
- Inline `pandas.query` filtering with a live status message.

### Prepare workspace
- Fill missing values (mean, median, mode, forward, backward, zero, constant) or drop incomplete rows.
- Remove duplicates, drop or rename columns, convert to numeric / datetime / category / text.
- Standard and min-max scaling, IQR-based outlier removal with an adjustable factor.
- Computed columns from expressions (`revenue / units`), group-by aggregation and pivot tables.
- Every mutation is a history step — full **undo/redo** with labelled steps.

### Statistics workspace
Descriptive statistics (incl. skewness, kurtosis, CV %), correlation matrices (Pearson, Spearman, Kendall),
frequency tables, Shapiro-Wilk normality, Welch and paired t-tests, one-way ANOVA, chi-square test of
independence and OLS regression — each with a plain-language interpretation panel.

### Visualise workspace
Ten themed chart types — line, area, bar, horizontal bar, scatter (with fitted trend line), histogram,
box, violin, pie and correlation heatmap — with grouping, zoom/pan toolbar and PNG/SVG/PDF export.

### Machine learning workspace
- **Regression**: linear, ridge, decision tree, random forest, gradient boosting, SVR — R², RMSE, MAE and cross-validated R².
- **Classification**: logistic regression, decision tree, random forest, gradient boosting, SVC — accuracy, weighted precision/recall/F1 and a confusion matrix.
- **Unsupervised**: K-Means (silhouette score, inertia, centroids) and PCA (explained variance).
- Training runs on a worker thread so the interface never freezes; predictions and clusters can be appended back to the dataset.

### Trust Center
- **Local sensitive-data scan** flags likely email, phone, IP-address and payment-card fields without storing detected values or sending the dataset anywhere.
- **Data contracts** enforce not-null, uniqueness, numeric ranges, allowed values, regular-expression formats and data freshness with severity levels.
- **Review-first quality controls**: recommended rules are explicit, editable and never mutate your data; every data mutation invalidates a prior quality result.
- Export a portable **JSON audit report** and include the latest Trust Center evidence in the styled HTML analysis report.
- `.dsproj` files preserve the data contract, while checks are deliberately re-run after restore to keep validation current.

### Reporting and projects
- One-click **styled HTML report** covering dataset overview, quality profile, sample rows, every analysis run in the session, the latest chart and the full processing log.
- `.dsproj` project files store the dataset together with its processing history.
- Export the working dataset to CSV, Excel, JSON or Parquet.

### Experience
Custom dark and light design system, keyboard shortcuts (`Ctrl+O` import, `Ctrl+Z/Y` undo/redo,
`Ctrl+R` report, `Ctrl+T` theme, `Ctrl+1…5` workspaces), recent-file list, live status bar and a
version-stamped executable with a native icon.

## Run from source

```bash
git clone https://github.com/Ali-Marandi/DataSense.git
cd DataSense
python -m venv .venv && .venv\Scripts\activate   # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Use **File ▸ Load sample dataset** (`Ctrl+Shift+S`) to explore the app with a generated retail dataset.

### Tests

```bash
pip install pytest
pytest -q
```

## Build the Windows executable yourself

```powershell
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean DataSense.spec
# optional installer (requires Inno Setup 6)
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DAppVersion=1.0.0 installer\DataSense.iss
```

Pushing a `v*` tag runs the same pipeline in GitHub Actions and publishes the installer,
portable archive and standalone executable to a GitHub release.

## Architecture

```text
main.py                 Application entry point (Qt bootstrap, icon, high-DPI)
core/
  data_manager.py       Loading, profiling, transformations, undo/redo, export
  statistics.py         Descriptive and inferential statistics
  ml.py                 Regression, classification, clustering, PCA
  report.py             Styled HTML report builder
  project.py            .dsproj save/load (zip + parquet + governance contract)
  governance.py         Data contracts, local PII classification and audit evidence
  version.py            Product metadata
ui/
  main_window.py        Menus, toolbar, session commands, reporting
  data_tab.py           Data workspace
  transform_tab.py      Prepare workspace
  analysis_tab.py       Statistics workspace
  visualization_tab.py  Charting workspace
  ml_tab.py             Machine learning workspace (threaded training)
  theme.py              Dark/light design system (single Qt stylesheet)
  widgets/              DataFrame table model, themed Matplotlib canvas
installer/DataSense.iss Inno Setup installer definition
DataSense.spec          PyInstaller build recipe
```

**Stack:** Python 3.11, PyQt6, pandas, NumPy, SciPy, scikit-learn, Matplotlib, PyArrow, PyInstaller, Inno Setup.

## License

MIT — see [LICENSE](LICENSE).
