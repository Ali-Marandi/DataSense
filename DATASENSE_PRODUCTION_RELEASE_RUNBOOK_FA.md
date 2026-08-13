# Runbook نهایی ادغام و انتشار production DataSense

## مرز نسخهٔ فعلی

DataSense v2.2.1 پیش‌تر منتشر شده است. تغییرهای بعدی شامل Schema Drift Guard، پایدارسازی آزمون‌های headless PyQt و مستندات مرتبط در commit محلی `c1390ba` قرار دارند و هنوز به remote ارسال نشده‌اند. بنابراین این runbook برای **انتشار نسخهٔ بعدی با شمارهٔ جدید** است؛ tag یا asset منتشرشدهٔ `v2.2.1` نباید بازنویسی شود.

pipeline موجود با push یک tag مطابق `v*` روی `windows-latest` اجرا می‌شود، Python 3.11 را نصب می‌کند، `python -m pytest -q` را اجرا می‌نماید، PyInstaller bundle می‌سازد، portable ZIP و Inno Setup installer را تولید و سه asset Windows را به GitHub Release الصاق می‌کند. workflow فعلی در `build.yml` شامل مرحلهٔ Authenticode code-signing یا generation checksum/SBOM نیست؛ عبارت «signed-ready installer» فقط به ساخت installer اشاره دارد، نه امضای دیجیتال واقعی. این کنترل‌ها باید پیش از ادعای release signed افزوده شوند.

## تصمیم نسخه و ownership

برای release بعدی یک شمارهٔ semantic version جدید مانند `v2.2.2` یا `v2.3.0` انتخاب کنید؛ نوع version به دامنهٔ تغییر و policy محصول بستگی دارد. اگر Schema Drift Guard یک feature جدید پایدار و visible برای مشتری است، minor release معمولاً منطقی‌تر است؛ اگر scope release صرفاً patch/backport باشد، patch version مناسب‌تر است. تصمیم نسخه باید توسط Product Owner و Release Manager ثبت شود.

| نقش | مسئولیت Go/No-Go |
|---|---|
| Release Manager | هماهنگی checklist، tag، release notes، approval و rollback decision. |
| Engineering Owner | review کد، پاسخ به failure CI و ownership regression. |
| Security Owner | secret scan، dependency/SBOM، code-signing و vulnerability exception. |
| QA Owner | اجرای smoke test Windows، acceptance Trust Center و evidence tests. |
| Data Steward | تایید policy پیش‌فرض Schema Drift و wording مستندات. |
| Support/Customer Success | اطلاع‌رسانی release، known issue و مسیر escalation. |

## مرحله ۰ — بازیابی اتصال و همگام‌سازی GitHub

ابتدا اتصال DNS/network را در محیطی که می‌خواهید release را از آن انجام دهید برقرار کنید. خطای قبلی `Could not resolve host: github.com` یک مشکل شبکه است، نه دلیل تعویض token. Credential افشاشده باید revoke شود؛ برای ورود جدید از GitHub CLI interactive login یا credential محدود و کوتاه‌عمر استفاده کنید و token را در command line یا remote URL قرار ندهید.

```bash
cd /home/ubuntu/datasense
git status --short
git fetch --prune origin
git log --oneline --left-right origin/main...main
```

اگر branch محلی فقط جلوتر است، ابتدا آن را به GitHub منتقل کنید. اگر branch حفاظت‌شده است یا `origin/main` تغییر جدید دارد، از branch release و Pull Request استفاده کنید، نه force push.

```bash
# فقط وقتی direct push طبق policy مجاز است
git push origin main

# مسیر ترجیحی برای branch حفاظت‌شده
git switch -c release/schema-drift-guard
git push -u origin release/schema-drift-guard
# سپس Pull Request به main، review و CI
```

## مرحله ۱ — کنترل‌های پیش از merge

| کنترل | فرمان/شاهد | معیار عبور |
|---|---|---|
| Working tree | `git status --short` | خالی، مگر فایل‌های reviewشدهٔ branch release. |
| Full regression | `python3 -m pytest -q` | در baseline فعلی: 79 passed و فقط 2 warning غیرمسدودکنندهٔ joblib. |
| whitespace | `git diff --check origin/main...HEAD` | بدون خطا. |
| Secret scan اولیه | `git grep -nEi '(ghp_|github_pat_|BEGIN .*PRIVATE KEY)' -- . ':!*.lock'` | خروجی واقعی secret نداشته باشد. |
| Dependency review | lock/requirements و advisory scanner سازمانی | vulnerability Critical بدون exception باز نباشد. |
| Schema Guard acceptance | baseline، added column مجاز، dtype/nullability breaking و persistence `.dsproj` | هر سناریو مطابق policy و test نتیجهٔ مورد انتظار دهد. |
| UI smoke | Trust Center در Windows built artifact باز شود | crash، import failure یا text clipping بحرانی نداشته باشد. |
| PR review | حداقل reviewerهای مقرر | approval و CI سبز. |

توجه کنید که scan سادهٔ regex جایگزین secret-scanning رسمی GitHub یا ابزار سازمانی نیست. اگر secret واقعی در history پیدا شد، push/release متوقف، credential revoke و history طبق policy بازنویسی شود.

## مرحله ۲ — آماده‌سازی نسخه و مستندات

این فایل‌ها باید در یک PR release review شوند:

```text
core/version.py                 # APP_VERSION = "X.Y.Z"
CHANGELOG.md                    # تغییرهای کاربرمحور و migration/known issue
RELEASE_NOTES.md                # خلاصه، assetها، validation و upgrade notes
README.md یا documentation       # در صورت تغییر مسیر نصب/کارکرد
```

پیش از tag، version در `core/version.py` را با release candidate تطبیق دهید. workflow فعلی version را از همین فایل می‌خواند اما تطابق tag GitHub با `APP_VERSION` را enforce نمی‌کند؛ Release Manager باید آن را دستی کنترل کند یا یک check CI برای جلوگیری از mismatch اضافه نماید.

Release notes باید صریحاً توضیح دهد که Schema Drift Guard چه چیزی را مانیتور می‌کند، policy پیش‌فرض چیست، baseline چگونه approve می‌شود و چه چیزی **هنوز** در release فعال نیست؛ به‌ویژه alert scheduler مرکزی، signed evidence، SAML/RBAC production rollout و certification نباید به‌اشتباه قابلیت active فرض شوند.

## مرحله ۳ — Release Candidate در Windows

CI GitHub برای release، `python -m pytest -q` را روی Windows اجرا می‌کند، سپس این artifactها را تولید می‌نماید:

| Asset | مسیر pipeline | پذیرش |
|---|---|---|
| Installer | `dist/DataSense-X.Y.Z-setup.exe` | نصب/حذف آزمایشی و launch موفق روی Windows تمیز. |
| Portable | `dist/DataSense-X.Y.Z-windows-x64-portable.zip` | unzip، launch بدون install و Trust Center usable. |
| Executable | `dist/DataSense/DataSense.exe` | launch، import نمونه و exit بدون error. |

پیش از انتشار عمومی، artifactهای CI را روی یک Windows VM یا دستگاه تمیز بررسی کنید. حداقل smoke شامل startup، import CSV، بازکردن Trust Center، ساخت baseline schema، تغییر dtype یا nullable، مشاهدهٔ `blocked`، export evidence JSON و open/save `.dsproj` است.

## مرحله ۴ — Code signing، SBOM و provenance

برای کاهش Windows SmartScreen friction و ایجاد trust زنجیرهٔ انتشار، مرحلهٔ بعدی ضروری است:

1. گواهی Authenticode را از secret manager/secure signing service دریافت کنید؛ فایل PFX یا password را در repository قرار ندهید.
2. `DataSense.exe` و setup executable را با timestamp server امضا کنید.
3. امضای Authenticode را روی artifact دانلودشده verify کنید.
4. SBOM را از dependencyهای Python و bundle تولید و به release attach کنید.
5. SHA-256 هر سه asset را در فایل `SHA256SUMS.txt` ایجاد، verify و attach کنید.
6. provenance build شامل commit SHA، tag، runner و زمان build را در release evidence نگه دارید.

تا پیش از اجرای واقعی این مراحل، نباید در release notes از «امضاشده» یا «دارای SBOM» استفاده شود.

## مرحله ۵ — Tag و انتشار GitHub

پس از merge شدن PR release به `main` و green شدن checks:

```bash
git switch main
git pull --ff-only origin main
python3 -m pytest -q

git tag -a vX.Y.Z -m "DataSense vX.Y.Z"
git show vX.Y.Z
git push origin vX.Y.Z
```

push tag باید workflow Windows را آغاز کند. در صفحهٔ Actions، job `Package Windows x64` را تا انتها مشاهده کنید. release تنها وقتی قابل‌انتشار تلقی می‌شود که test، bundle، portable archive، installer و upload/publish asset موفق باشند. اگر job شکست خورد، tag منتشرشده را overwrite نکنید؛ failure را تحلیل، patch commit ایجاد و tag/version جدید طبق policy منتشر کنید.

## مرحله ۶ — Go/No-Go برای انتشار عمومی

| حوزه | شرط Go | شرط No-Go |
|---|---|---|
| Repository | `main` review/CI سبز، secret scan clean | conflict، unreviewed commit، branch protection bypass. |
| آزمون | 79+ test یا baseline موردتایید release پاس | failure، flaky test unresolved یا smoke Windows شکست‌خورده. |
| Version | tag و `APP_VERSION` یکسان؛ changelog کامل | mismatch یا بازنویسی tag قبلی. |
| Security | credential امن، signing/SBOM status صریح | secret افشاشده، ادعای signing بدون evidence. |
| Artifact | سه asset دانلود و sanity-check شده | setup/portable/EXE ناقص یا virus false-positive unresolved. |
| محصول | Schema Guard explanation و policy defaults مستند | user-facing behavior مبهم یا migration بدون راهنما. |
| عملیات | support owner، known issue و rollback owner حاضر | مسئول incident/rollback مشخص نیست. |

## مرحله ۷ — نظارت پس از انتشار

در ۲۴ تا ۷۲ ساعت اول، dashboard Actions، issue tracker، crash report، download integrity و feedback مشتریان پایلوت را مانیتور کنید. برای Schema Drift Guard، support باید ability تشخیص `not configured`، `compatible` و `blocked` را داشته باشد و evidence JSON privacy-safe را فقط با approval مشتری دریافت کند. Alert automation مرکزی هنوز feature آینده است؛ تا قبل از استقرار Control Plane، هیچ SLA خودکار برای notification ادعا نشود.

## Rollback و incident response

GitHub Release و tag immutable هستند؛ rollback نباید با جایگزینی asset زیر همان version انجام شود. اگر failure بحرانی کشف شد، release را در GitHub به Draft/Pre-release منتقل یا advisory منتشر کنید، asset معیوب را از دسترس عمومی خارج کنید طبق policy، و patch release با version جدید بسازید. برای مشکل محدود desktop، راهنمای workaround ارائه دهید. برای secret یا supply-chain incident، release distribution را متوقف، credential را revoke، incident commander تعیین و مشتریان متاثر را طبق برنامهٔ پاسخ به رخداد مطلع کنید.

## شواهدی که باید نگهداری شود

Release packet باید شامل PR/approval، commit SHA، نتیجهٔ test و JUnit، Windows smoke evidence، SBOM، signature verification، SHA256SUMS، release notes، asset URLs، monitoring owner و تصمیم Go/No-Go باشد. این packet پاسخ‌گویی audit را آسان می‌کند و برای checklist SOC 2/ISO 27001 قابل‌ارجاع است.
