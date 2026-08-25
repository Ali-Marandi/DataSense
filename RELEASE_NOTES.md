# DataSense 2.3.0 — Verified Local Exports

DataSense 2.3.0 strengthens the Windows desktop release with a **verified export workflow** for sensitive analytical work. Analysts can now create a styled HTML report or interactive dashboard only after the active Trust Center evidence passes its local quality and schema gates. The workflow produces a companion, signed receipt that binds the permitted action to current metadata-only evidence.

## Downloads

| File | Use it for |
|---|---|
| `DataSense-2.3.0-setup.exe` | Recommended Windows installer with Start-menu shortcut, optional desktop shortcut, and uninstaller. |
| `DataSense-2.3.0-windows-x64-portable.zip` | Portable bundle; unzip and run `DataSense.exe` without installation. |
| `DataSense.exe` | Standalone executable from the packaged bundle for controlled deployment tooling. |

Windows 10 or Windows 11, 64-bit, is required. Python is bundled and is not required on the user’s computer.

## Verified export workflow

Choose **File → Export verified artifact** to select either an analysis report or an interactive dashboard. The workflow requires current Trust Center checks and a local HMAC signing key. DataSense evaluates the requested internal artifact against the signed evidence and only writes the HTML artifact when the decision is `allow`.

| Output | Behaviour |
|---|---|
| Verified HTML artifact | Written only after quality and schema gates permit the requested action. |
| `*.trust-receipt.json` companion file | Signed, metadata-only decision evidence stored next to the requested artifact. |
| Blocked or approval-required action | The HTML artifact is not written; a metadata-only receipt records the decision and reason codes for offline review. |

> The signing key is never included in the receipt and must remain outside source control. The receipt does not include raw dataset values, local source paths, recipient details, URLs, prompts, or credentials.

## Reliability and packaging

The Windows build and release workflows now install both desktop and Enterprise Control Plane test dependencies before invoking the complete regression suite. This removes the prior gap in which the packaging workflows collected Control Plane tests without installing their declared dependencies.

DataSense 2.3.0 retains its full desktop studio for data import, profiling, preparation, statistics, visualization, SQL analysis, time series, machine learning, AutoML, dashboards, local project files, and Trust Center evidence.

## Upgrade note

Open existing `.dsproj` projects normally. Existing data and analysis workflows are preserved. To use verified export, create or review a Trust Center contract, run the current checks, and select a local signing key when prompted.
