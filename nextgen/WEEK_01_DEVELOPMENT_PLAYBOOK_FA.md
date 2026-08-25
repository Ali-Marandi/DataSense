# برنامهٔ اجرایی تفصیلی هفتهٔ اول توسعهٔ DataSense

**هدف هفته:** یک Alpha محلی و قابل‌نصب بسازید که یک CSV یا دادهٔ نمونه را باز کند، قرارداد کیفیت را اجرا کند و در صورت تأیید کنترل‌ها یک گزارش HTML با رسید metadata-only تولید کند. این هفته به معنای ساخت «تمام DataSense» نیست؛ هدف، تثبیت مرزهای معماری و اثبات مسیر ارزش محوری است.

> **خروجی پایان هفته:** مسیر `Explore → Prepare & Validate → Deliver` در Windows، همراه با آزمون‌های هسته، UI smoke و بستهٔ قابل‌ساخت PyInstaller.

## قوانین کاری هفته

| قانون | اجرا |
|---|---|
| مسیر ارزش اول | قبل از ساخت ML، AutoML، cloud execution، SSO یا connector جدید، مسیر import تا verified export سبز باشد. |
| دادهٔ واقعی | هرگز فایل دادهٔ واقعی مشتری را در issue، log، screenshot، test fixture یا ابزار tracking قرار ندهید. |
| تغییر کوچک | هر task باید با یک commit کوچک، آزمون و معیار پذیرش قابل‌بازبینی تمام شود. |
| مرز UI | widgetهای PyQt فقط تعامل و نمایش هستند؛ منطق pandas، policy یا I/O در `core/` باقی می‌ماند. |
| release gate | هیچ build قابل‌ارسال بدون test، smoke launch و hash artifact آماده نشود. |

---

## روز ۱ — Bootstrap، قرارداد معماری و baseline کیفیت

### هدف روز

محیط توسعه تکرارپذیر، ساختار پوشهٔ رسمی و یک baseline قابل‌اندازه‌گیری ایجاد شود. در پایان روز، همهٔ اعضا باید بتوانند از clone تازه، برنامه را اجرا و تست را سبز کنند.

| تسک | فایل/فرمان | خروجی مورد انتظار |
|---|---|---|
| ساخت محیط | `python -m venv .venv`، سپس نصب editable | محیط ایزوله با Python 3.11+ و PyQt6/pandas/pytest/PyInstaller |
| تثبیت dependencyها | `pyproject.toml` و `requirements.txt` | نسخه‌های قابل‌قبول برای pandas، pyarrow، PyQt6، pytest و PyInstaller |
| ساختار پروژه | `app/`، `core/`، `ui/`، `tests/` | import graph مشخص و بدون circular import |
| ADR-001 | `docs/adr/001-local-first.md` | تصمیم local-first، مرز داده و ممنوعیت telemetry خام ثبت شود |
| baseline test | `QT_QPA_PLATFORM=offscreen pytest` | خروجی تست اولیه سبز |

### گام‌های کدنویسی

1. از پوشهٔ `datasense_windows_boilerplate` یک repository مستقل بسازید یا آن را به شاخهٔ `architecture-alpha` منتقل کنید.
2. `pyproject.toml` را تنها منبع وابستگی در نظر بگیرید و `requirements.txt` را برای نصب سریع/CI نگه دارید.
3. در `app/bootstrap.py` توابع `create_application()`، `app_data_dir()` و `configure_logging()` را حفظ کنید. مسیر لاگ باید زیر `AppDataLocation` باشد، نه کنار EXE.
4. در `.gitignore` مسیرهای `.dsproj`، `build/`، `dist/`، `.venv/` و cacheها را کنترل کنید.
5. فایل `docs/adr/001-local-first.md` را با این قالب ایجاد کنید:

```md
# ADR-001: Local-first data boundary

## Context
DataSense analyses customer datasets that may contain sensitive information.

## Decision
Raw datasets, paths, column names and query contents remain local by default.
Network calls are opt-in and are limited to entitlement, update metadata or redacted telemetry.

## Consequences
All cloud features must name their payload, purpose, retention and opt-in mechanism.
```

### آزمون و معیار پذیرش

```bash
python -m pip install -e .[dev,package]
QT_QPA_PLATFORM=offscreen pytest
python -m py_compile main.py app/*.py core/**/*.py ui/*.py
```

- برنامه بدون exception import شود.
- `pytest` سبز باشد.
- هیچ credential، کلید یا dataset fixture واقعی در repository نباشد.
- **نام commit پیشنهادی:** `chore: bootstrap local-first desktop alpha`.

---

## روز ۲ — هستهٔ داده و مدل وضعیت برنامه

### هدف روز

یک API محدود و تست‌پذیر برای import و profiling ایجاد شود. UI نباید `pandas.read_csv` یا `DataFrame` mutation مستقیم انجام دهد.

| تسک | فایل اصلی | تعریف اتمام |
|---|---|---|
| Dataset profile | `core/data/model.py` | `DatasetProfile` immutable با rows، columns، missing، duplicates، memory و summary ستون‌ها |
| Data service | `core/data/service.py` | `load_csv()` و `profile()` همراه با errorهای قابل‌فهم |
| Application state | `app/composition.py` | state فقط شامل frame فعال، source label، contract و quality report باشد |
| test data | `tests/test_data_service.py` | CSV معتبر، CSV خالی و فایل مفقود پوشش داده شود |

### گام‌های کدنویسی

1. `DatasetProfile` را `frozen=True` نگه دارید تا UI نتواند خروجی profiling را تغییر دهد.
2. در `load_csv`، وجود فایل و خالی نبودن frame را اعتبارسنجی کنید. encoding/sniffing delimiter در هفتهٔ اول لازم نیست؛ آن را issue آینده ثبت کنید.
3. در `profile` فقط aggregateهای امن تولید کنید. مقادیر خام ستون یا `head()` نباید جزو telemetry یا evidence آینده باشند.
4. `ApplicationState` را با `default_factory` بسازید؛ هرگز DataFrame یا list mutable را default مستقیم ندهید.
5. در پایان روز، UI با `services.data.profile(frame)` وضعیت را render کند.

### تست‌های لازم

```python
def test_profile_counts_missing_and_duplicates(tmp_path):
    path = tmp_path / "orders.csv"
    path.write_text("order_id,revenue\nA-1,10\nA-1,\n", encoding="utf-8")
    frame = DataService().load_csv(path)
    profile = DataService().profile(frame)
    assert profile.rows == 2
    assert profile.missing_cells == 1
    assert profile.duplicate_rows == 0  # duplicate row، نه duplicate identifier
```

### معیار پذیرش

- فایل CSV نمونه در UI باز شود و metrics نمایش داده شود.
- خطای فایل مفقود با نام فایل و بدون stack trace در UI دیده شود.
- برای ۱۰۰ هزار ردیف، profiling در worker/زمان‌بندی جدا issue شده باشد؛ در هفتهٔ اول implementation synchronous فقط برای alpha پذیرفته است.
- **نام commit پیشنهادی:** `feat(core): add local dataset service and profile model`.

---

## روز ۳ — قرارداد داده و تصمیم کیفیت

### هدف روز

کیفیت داده به یک domain service deterministic تبدیل شود که بدون PyQt قابل‌آزمون است. قرارداد ابتدایی فقط `not_null` و `unique` را پشتیبانی می‌کند؛ افزودن ruleهای بیشتر بعداً و با test انجام می‌شود.

| تسک | فایل اصلی | تعریف اتمام |
|---|---|---|
| Rule model | `core/governance/contracts.py` | `DataQualityRule`، `RuleResult` و severityهای محدود |
| Evaluation | `DataContract.evaluate(frame)` | تصمیم approved/block بر اساس critical/high failures |
| UI adapter | `ui/main_window.py` | نمایش PASS/FAIL، تعداد violation و دلیل قابل‌اقدام |
| tests | `tests/test_governance.py` | happy path، duplicate ID، ستون مفقود و null |

### گام‌های کدنویسی

1. قرارداد default را روی ستون `order_id` بسازید تا template عملیات بتواند از آن استفاده کند.
2. نتیجه باید شامل `passed`، `violations` و `detail` باشد؛ UI نباید خودش duplicate را محاسبه کند.
3. فقط failureهای `critical` و `high` باید خروجی verified را block کنند. این policy را به constant یا `QualityPolicy` جدا منتقل کنید، نه if پراکنده در UI.
4. برای column مفقود، report را block کنید و detail بنویسید: `Required column is missing.`
5. summary report را در state نگه دارید؛ هر import جدید باید quality report قبلی را invalid کند.

### تست‌های لازم

```python
def test_missing_required_column_blocks_contract():
    frame = pd.DataFrame({"invoice_id": ["I-1"]})
    report = DataContract.default().evaluate(frame)
    assert not report.approved
    assert report.blocking_failures[0].rule.column == "order_id"
```

### معیار پذیرش

- کاربر با دادهٔ نمونه بتواند `Run quality checks` را بزند و نتیجه را در UI ببیند.
- duplicate در `order_id` خروجی approved را false کند.
- import مجدد، گزارش قبلی را پاک کند.
- **نام commit پیشنهادی:** `feat(governance): add deterministic starter data contract`.

---

## روز ۴ — verified export و رسید حریم‌خصوصی‌محور

### هدف روز

قابلیت تمایزبخش DataSense ساخته شود: گزارش HTML فقط با کیفیت approved نوشته شود و در هر حالت receipt metadata-only کنار فایل ساخته شود.

| تسک | فایل اصلی | تعریف اتمام |
|---|---|---|
| Decision service | `core/delivery/verified_export.py` | `decide()` با خروجی allow/block و reason code |
| Receipt | همان فایل | payload canonical، hash و HMAC برای alpha |
| HTML report | همان فایل | summary aggregate بدون دادهٔ خام |
| tests | `tests/test_verified_export.py` | approved output، blocked output و redaction |

### گام‌های کدنویسی

1. `VerifiedExportService.decide()` را قبل از هر file write اجرا کنید.
2. اگر `quality is None` است، فقط receipt با `quality_check_missing` بنویسید و artifact را ننویسید.
3. اگر quality block شد، receipt با `quality_gate_blocked` بنویسید و artifact را ننویسید.
4. اگر approved شد، ابتدا receipt را بنویسید، سپس HTML را بنویسید. در نسخهٔ بعدی هر دو با transaction/temp file اتمیک شوند.
5. payload receipt فقط schema، timestamp، policy version، aggregate dataset metrics، outcome و reason codes داشته باشد.
6. کلید hard-coded فقط برای alpha است. در ticket بعدی interface `SigningKeyProvider` با DPAPI/Credential Manager ایجاد کنید.

### تست‌های لازم

```python
def test_receipt_never_contains_raw_order_identifier(tmp_path):
    frame = DataService().sample_dataset()
    profile = DataService().profile(frame)
    quality = DataContract.default().evaluate(frame)
    _, receipt = VerifiedExportService().export_html(tmp_path / "r.html", frame, profile, quality, b"key")
    assert "SO-1001" not in receipt.read_text(encoding="utf-8")
```

### معیار پذیرش

- حالت approved: `report.html` و `report.html.trust-receipt.json` هر دو ایجاد شوند.
- حالت blocked: فقط receipt ساخته شود.
- receipt هیچ مقدار خام dataset یا مسیر local نداشته باشد.
- **نام commit پیشنهادی:** `feat(delivery): add metadata-only verified export receipt`.

---

## روز ۵ — Desktop shell و جریان سه‌مرحله‌ای

### هدف روز

رابط PyQt6 نباید demo تصادفی باشد؛ باید دقیقاً سه جریان معماری را قابل‌دیدن کند: Explore، Prepare & Validate و Deliver.

| تسک | فایل اصلی | تعریف اتمام |
|---|---|---|
| Main shell | `ui/main_window.py` | navigation سمت چپ و `QStackedWidget` |
| Explore | همان فایل | Open CSV، Load sample، profile summary |
| Validate | همان فایل | اجرای قرارداد و نمایش rule results |
| Deliver | همان فایل | export verified و نمایش مسیر receipt |
| styling | `ui/theme.py` | dark theme محدود، کنتراست مناسب و focus قابل‌مشاهده |

### گام‌های کدنویسی

1. `MainWindow` فقط یک dependency بگیرد: `Services` از composition root.
2. `build_services()` در `app/composition.py` تنها محل ساخت `DataService`، `VerifiedExportService` و `ApplicationState` باشد.
3. برای هر دکمه، handler کوتاه نوشته شود و منطق را به core بسپارد.
4. پیام‌های خطا با `QMessageBox` باید actionable باشند؛ stack trace فقط در local log.
5. در پایان، test UI فقط construction window را بررسی کند؛ تعامل‌های پیچیده در unit test core باقی بمانند.

### معیار پذیرش

- `QT_QPA_PLATFORM=offscreen python main.py` حداقل ۵ ثانیه بدون crash زنده بماند.
- با Load sample، status شامل تعداد rows/columns باشد.
- بدون dataset، `Run quality checks` و Export پیام مناسب بدهند.
- **نام commit پیشنهادی:** `feat(ui): add three-flow PyQt desktop shell`.

---

## روز ۶ — persistence، مجوز و telemetry با مرز درست

### هدف روز

مرزهای تجاری و عملیاتی را بدون ایجاد backend پیچیده بسازید. داده باید محلی ذخیره شود، feature gate قابل‌تعویض باشد و telemetry فقط در صورت رضایت کاربر queue شود.

| تسک | فایل اصلی | تعریف اتمام |
|---|---|---|
| Project store | `core/projects/store.py` | ZIP + Parquet + manifest JSON و atomic replacement |
| Entitlement | `core/licensing/entitlement.py` | alpha plan، feature set و expiry mock |
| Telemetry | `core/telemetry/events.py` | event allowlist و queue محلی فقط با consent |
| tests | `tests/test_project_store.py` و `tests/test_telemetry.py` | persistence و redaction تست شوند |

### گام‌های کدنویسی

1. `.dsproj` را با `zipfile` و Parquet بسازید؛ pickle استفاده نکنید.
2. `os.replace()` تنها بعد از موفقیت کامل staging اجرا شود.
3. entitlement را interface نگه دارید؛ UI فقط `feature_gate.allows("verified_export")` را بخواند.
4. eventهایی با نام ناآشنا یا field ناآشنا باید exception بدهند یا field را حذف کنند.
5. default consent برابر false است. برنامه نباید queue file ایجاد کند مگر کاربر رضایت دهد.

### معیار پذیرش

- project save با archive قابل‌خواندن و `manifest.json` درست انجام شود.
- event دارای `file_name` یا `column_values` در queue ذخیره نشود.
- feature gate alpha برای `verified_export` true باشد.
- **نام commit پیشنهادی:** `feat(platform): add local project store and privacy-safe boundaries`.

---

## روز ۷ — کیفیت انتشار، بسته‌بندی و review پایان هفته

### هدف روز

یک release candidate داخلی بسازید، مسیر نصب/اجرا را بررسی کنید و شواهد مشتری/فنی هفته را به backlog هفتهٔ دوم تبدیل کنید.

| تسک | فرمان/فایل | خروجی |
|---|---|---|
| اجرای کامل tests | `QT_QPA_PLATFORM=offscreen pytest` | test suite سبز |
| بررسی syntax | `python -m py_compile ...` | importable modules |
| بسته‌بندی | `pyinstaller --noconfirm --clean --name DataSenseAlpha --windowed main.py` | `dist/DataSenseAlpha/` |
| smoke bundle | اجرای EXE روی Windows VM یا Linux smoke برای توسعه | window بدون crash باز شود |
| SBOM اولیه | `pip list --format=json > build/sbom-python.json` | فهرست dependency با version |
| review | `docs/week-01-review.md` | metrics، debt، bugs و تصمیم هفته بعد |

### checklist پایان هفته

| مورد | شرط قبولی |
|---|---|
| مسیر ارزش | sample data تا verified export بدون exception انجام شود. |
| trust | duplicate ID، missing quality check و missing column artifact را block کنند. |
| privacy | receipt فاقد raw values/path باشد؛ telemetry پیش‌فرض خاموش باشد. |
| UX | سه flow قابل‌ناوبری و پیام‌های empty state واضح باشند. |
| build | PyInstaller bundle ایجاد شود و برنامه از bundle launch شود. |
| customer | حداقل ۵ مصاحبه یا ۱۰ دعوت مصاحبه با evidence log انجام شده باشد. |
| backlog | هفتهٔ دوم فقط با RICE و شواهد customer rank شده باشد. |

**نام commit پیشنهادی:** `chore(release): prepare alpha-1 validation bundle`.

---

## جلسهٔ review پایان هفته (۴۵ دقیقه)

| بخش | پرسش تصمیم‌ساز | تصمیم ممکن |
|---|---|---|
| Product | آیا کاربر مسیر ۳ مرحله‌ای را بدون توضیح فهمید؟ | اصلاح UI یا تغییر copy؛ افزودن feature ممنوع مگر P0 |
| Trust | آیا دلیل block برای کاربر قابل‌اقدام بود؟ | بهبود rule detail یا default contract |
| Engineering | چه crash/import/build failureی دیده شد؟ | hardening sprint یا ادامهٔ feature |
| Market | کدام pain تکراری و کدام vertical بیشترین response داشت؟ | انتخاب beachhead یا تکرار discovery |
| Economics | آیا کسی برای Design Partner یا قیمت Pro سیگنال پرداخت داد؟ | تست pricing یا بازطراحی offer |

## خروجی‌های تحویلی هفتهٔ اول

1. `datasense_windows_boilerplate/` با ۵ آزمون عبورکرده و قابلیت اجرای headless.
2. یک Alpha local-only شامل CSV import، profile، starter contract و verified export.
3. ADR-001 دربارهٔ local-first data boundary.
4. سه template مسئله‌محور در حد specification: Monthly Operations، Supplier Quality و Month-end Variance.
5. فهرست lead، یادداشت مصاحبه و تصمیم اولیهٔ vertical.
6. RC داخلی PyInstaller به همراه hash/SBOM اولیه.

> اگر یکی از خروجی‌های ۱ تا ۳ ناقص است، هفتهٔ دوم نباید با connector، AI agent یا cloud control plane شروع شود. ابتدا مسیر value و اعتماد را پایدار کنید.
