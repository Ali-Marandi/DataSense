# DataSense Windows Boilerplate

این پوشه یک skeleton مستقل و قابل‌اجرای Alpha بر پایهٔ معماری local-first DataSense است. این بسته به‌صورت مستقیم مخزن منتشرشدهٔ DataSense را تغییر نمی‌دهد.

## قابلیت‌های پیاده‌سازی‌شده

| حوزه | قابلیت Alpha |
|---|---|
| Desktop UI | پنل PyQt6 با Dashboard، Explore، Prepare & Validate و Deliver |
| دادهٔ محلی | import CSV/TSV/TXT، validation ورودی، profile aggregate و preview محدود local |
| تحلیل | قرارداد `ProcessingModule` و diagnostics سری زمانی بدون تولید سیگنال معاملاتی |
| Trust | data contract، quality report، verified HTML export و receipt metadata-only قابل‌راستی‌آزمایی |
| signing | provider تزریقی HMAC برای Alpha؛ نقطهٔ جایگزینی آماده برای DPAPI/Credential Manager |
| persistence | پروژهٔ نسخه‌دار `.dsproj` با Parquet، load، migration، atomic save و backup |
| entitlement | feature gate با stateهای active/grace/expired و cache محلی atomic |
| privacy | telemetry opt-in، field allowlist، retention و acknowledgement محلی |
| quality | unit test هسته، UI smoke و اعتبارسنجی ساختار release pipeline |

## اجرای محلی

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,package]"
python main.py
python -m pytest
```

برای آزمون headless در Linux:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest
```

## ساخت بستهٔ محلی

```powershell
python scripts/build_release.py --version 0.1.0-alpha
```

این فرمان testها را اجرا می‌کند، bundle یک‌پوشه‌ای PyInstaller می‌سازد و SBOM، manifest و checksum محلی تولید می‌کند. برای debug سریع می‌توان `--skip-tests` را استفاده کرد، اما این گزینه برای release ممنوع است.

## Windows installer و GitHub Actions

فایل‌های زیر زنجیرهٔ release ویندوزی را تکمیل می‌کنند:

| فایل | نقش |
|---|---|
| `.github/workflows/windows-exe.yml` | test، PyInstaller، Inno Setup، smoke test، manifest، artifact و tag-release |
| `installer/DataSense.iss` | installer per-user x64 با support برای upgrade/uninstall |
| `scripts/build_release.py` | build bundle و SBOM |
| `scripts/finalize_release.py` | تولید ZIP/checksum/manifest پس از code signing |
| `CI_CD_GITHUB_ACTIONS_EXE_FA.md` | راهنمای عملیات، branch protection، secrets و code signing |

> **کنترل انتشار:** release tag فقط هنگامی منتشر می‌شود که `WINDOWS_CERTIFICATE_BASE64`، `WINDOWS_CERTIFICATE_PASSWORD` و `WINDOWS_TIMESTAMP_URL` در GitHub Actions Secrets تنظیم شده باشند. workflow فایل EXE و installer را قبل از تولید ZIP و checksum امضا می‌کند. `FileHmacSigningKeyProvider` صرفاً برای رسیدهای اعتماد Alpha است و باید پیش از production با provider محافظت‌شدهٔ ویندوز جایگزین شود.

## محدودهٔ تحلیل مالی

`FINANCIAL_ANALYTICS_MODULE_ROADMAP_FA.md` مسیر امن توسعهٔ diagnostics سری زمانی، ARIMA/GARCH/VaR، بهینه‌سازی، مدل‌های فازی و research trackهای پیشرفته را توضیح می‌دهد. در Alpha هیچ معامله، اجرای سفارش یا توصیهٔ سرمایه‌گذاری تولید نمی‌شود.
