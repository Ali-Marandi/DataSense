# DataSense 2.2.1 — Windows Packaging Hotfix

DataSense 2.2.1 is the production packaging patch for the **Trusted Analytics** release. It preserves the Trust Center, data contracts, audit evidence and desktop stability repairs introduced in 2.2.0, while correcting the Windows pipeline so it installs and invokes the regression runner deterministically before packaging.

## Downloads

| File | Use it for |
|---|---|
| `DataSense-2.2.1-setup.exe` | Recommended installer with Start-menu shortcut, optional desktop shortcut and uninstaller. |
| `DataSense-2.2.1-windows-x64-portable.zip` | Portable bundle; unzip it and run `DataSense.exe` without installation. |
| `DataSense.exe` | Standalone executable from the packaged bundle for controlled deployment tooling. |

Windows 10 or Windows 11, 64-bit, is required. Python is bundled and is not required on the user’s computer.

## Trust Center

Trust Center does not transmit the active dataset. It provides a local sensitive-data scan that identifies likely email addresses, telephone numbers, IP addresses and payment-card patterns without retaining detected values. Findings are signals for review, not a legal classification or automated access-control decision.

Data contracts let an analyst define repeatable acceptance criteria. The initial rule set supports populated-value, uniqueness, numeric range, allowed-value, regular-expression and timestamp-freshness controls. Every rule has an explicit severity, and recommended rules are visible and editable before use. Running a check produces a weighted quality score together with `Trusted`, `Needs attention`, `Blocked`, or `Not configured` status. A data mutation invalidates the prior result automatically so stale evidence is never presented as current.

| Output | Purpose |
|---|---|
| Trust Center table | Review each control, observed condition, expectation, violations and error state. |
| JSON audit evidence | Attach deterministic, portable validation evidence to an approval process, ticket or archive. |
| Styled HTML analysis report | Includes the current Trust Center summary and control results when checks were run. |
| `.dsproj` project | Preserves the contract definition; DataSense intentionally asks the user to rerun validation after restoring a project. |

## Included platform capabilities

DataSense remains a full desktop studio for data import, quality profiling, preparation, statistics, visualisation, SQL analysis, time series, machine learning, AutoML, dashboards, local project files and styled reports. The release pipeline builds the Windows x64 bundle, portable archive and installer from the tagged source revision; it also runs regression tests before publishing release assets.

## Validation performed

The release candidate passed the complete automated suite, including dedicated contract, sensitive-data scanning, project persistence and off-screen desktop startup coverage. The PyInstaller recipe was additionally exercised in a Linux validation environment; Windows release artifacts are built only by the dedicated `windows-latest` GitHub Actions pipeline.

## Upgrade note

Open existing projects normally. Their datasets and earlier analysis features are preserved. Existing projects do not contain a data contract until one is created in Trust Center.
