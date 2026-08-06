## DataSense 1.0.0

First commercial-grade release of DataSense — a desktop data analysis studio for Windows.

### Downloads
| File | Use it for |
| --- | --- |
| `DataSense-1.0.0-setup.exe` | Recommended installer (Start menu + desktop shortcut, uninstaller) |
| `DataSense-1.0.0-windows-x64-portable.zip` | Portable build — unzip and run `DataSense.exe`, no installation |

### What's inside
- **Data workspace** — import CSV, TSV, Excel, JSON, Parquet and SQLite; KPI overview, virtualised preview of large tables and a per-column quality profile (types, missing %, uniqueness, spread).
- **Prepare workspace** — fill or drop missing values, deduplicate, convert types, standardise/min-max scale, IQR outlier removal, computed columns, pandas-query filtering, group-by aggregation and pivot tables, all with full undo/redo history.
- **Statistics workspace** — descriptive statistics, Pearson/Spearman/Kendall correlation matrices, frequency tables, Shapiro-Wilk normality, two-sample and paired t-tests, one-way ANOVA, chi-square independence and OLS regression, each with a plain-language interpretation.
- **Visualise workspace** — ten chart types (line, area, bar, horizontal bar, scatter with trend line, histogram, box, violin, pie, correlation heatmap) with themed rendering, zoom/pan toolbar and PNG/SVG/PDF export.
- **Machine learning workspace** — regression and classification (linear/ridge/logistic, decision tree, random forest, gradient boosting, SVM) with train/test split, cross-validated scores, feature importance and confusion matrices, plus K-Means clustering and PCA; training runs off the UI thread.
- **Reporting & projects** — one-click styled HTML report of the session, `.dsproj` project files that store the dataset with its processing history, and dataset export to CSV/Excel/JSON/Parquet.
- **Polished UI** — custom dark and light design system, keyboard shortcuts, recent files, live status bar and a signed version-stamped executable.

### Requirements
Windows 10 or 11 (64-bit). No Python installation required.
