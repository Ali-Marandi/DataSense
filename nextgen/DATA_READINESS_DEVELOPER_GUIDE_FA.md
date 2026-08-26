# راهنمای توسعه‌دهندگان `DataReadinessInsightsModule`

**وضعیت:** Alpha، قرارداد داخلی پایدار در سطح `v1`  
**نسخهٔ ماژول:** `data-readiness-insights/v1`  
**مسیر پیاده‌سازی:** `core/analysis/data_readiness.py`

## هدف و مرز معماری

`DataReadinessInsightsModule` یک ماژول **محلی، قطعی و صرفاً توصیفی** برای تشخیص آمادگی اولیهٔ یک `pandas.DataFrame` است. خروجی آن به‌جای نگهداری یا نمایش مقادیر سلولی، فقط شامل شمارش‌های تجمیعی، نام ستون‌ها در هشدارها و یک امتیاز heuristic است. این ماژول داده را ارسال، ذخیره، impute، پیش‌بینی یا تبدیل نمی‌کند و نباید به‌عنوان موتور توصیه، تصمیم مالی، ارزیابی اعتبار، یا تأیید کیفیت کسب‌وکاری تلقی شود.

> امتیاز آمادگی یک **heuristic محصولی** است؛ نه یک معیار آماری اعتبارسنجی‌شده، نه گواهی کیفیت داده و نه مبنای تصمیم‌گیری خودکار. هر کاربرد پرریسک باید قواعد حوزه، معیار پذیرش، بازبینی انسانی و اعتبارسنجی مستقل خود را اضافه کند.

| مسئولیت ماژول | خارج از دامنهٔ ماژول |
|---|---|
| شمارش missingness، non-finite، outlierهای IQR و ستون‌های non-numeric پرکاردینال | نمایش یا خروجی‌گرفتن ردیف‌های خام و مقادیر نمونه |
| تولید `ProcessingResult` immutable-compatible برای UI، گزارش و pipeline | mutation، پاک‌سازی، imputation یا حذف داده |
| تشخیص structural برای اولویت‌بندی بررسی انسان | پیش‌بینی، سیگنال معاملاتی، توصیهٔ مالی یا اجرای تراکنش |
| اجرای local-only و deterministic برای ورودی/config یکسان | telemetry شبکه‌ای، اتصال broker/API یا نتیجه‌گیری علّی |

## قرارداد عمومی

ماژول با `ProcessingModule` سازگار است. این protocol در `core/analysis/contracts.py` تعریف شده و امضای اجرایی آن چنین است:

```python
from core.analysis.contracts import ProcessingContext, ProcessingResult
from core.analysis.data_readiness import DataReadinessConfig, DataReadinessInsightsModule

module = DataReadinessInsightsModule(
    DataReadinessConfig(
        iqr_multiplier=1.5,
        high_cardinality_ratio=0.9,
        minimum_numeric_observations=4,
        readiness_threshold=70,
    )
)
result: ProcessingResult = module.process(frame, ProcessingContext())
```

`ProcessingContext` در نسخهٔ فعلی برای compatibility دریافت می‌شود، اما عمداً گزینه‌ای را نمی‌خواند و تغییری در رفتار ایجاد نمی‌کند. نسخه‌های بعدی فقط با تغییر صریح قرارداد و آزمون سازگاری می‌توانند معنای گزینه‌های context را اضافه کنند.

| عنصر | نوع | قرارداد |
|---|---|---|
| `frame` | `pandas.DataFrame` | الزامی است؛ نام ستون‌ها باید یکتا باشند. DataFrame mutation نمی‌شود. |
| `context` | `ProcessingContext` | الزامی برای protocol؛ در `v1` بی‌اثر است. |
| `module_id` | `str` | همیشه `data-readiness-insights/v1` است. |
| خروجی | `ProcessingResult` | `summary` فقط metadata تجمیعی، `warnings` فقط متن و نام ستون، بدون cell value یا source path. |

ورودی غیر `DataFrame` با `TypeError` و نام ستون تکراری با `ValueError` رد می‌شود. این ردکردن عمدی است؛ نام ستون تکراری باعث می‌شود نسبت‌دادن هشدار به ستون معنادار نباشد.

## پیکربندی و اعتبارسنجی

`DataReadinessConfig` یک dataclass با `frozen=True` است تا پس از ایجاد تغییر نکند. پارامترها همگی non-sensitive هستند و نباید از دادهٔ کاربر مشتق یا در telemetry ثبت شوند.

| فیلد | پیش‌فرض | اعتبارسنجی | نقش |
|---|---:|---|---|
| `iqr_multiplier` | `1.5` | بزرگ‌تر از صفر | ضریب فاصلهٔ IQR برای تعیین outlierهای عددی. |
| `high_cardinality_ratio` | `0.9` | در بازهٔ `(0, 1]` | اگر `nunique / populated_rows` به این حد برسد، ستون non-numeric احتمالاً identifier است. |
| `minimum_numeric_observations` | `4` | حداقل `4` | حداقل تعداد مقدار finite برای اجرای تشخیص IQR در یک ستون. |
| `readiness_threshold` | `70` | عدد صحیح در بازهٔ `[0, 100]` | مرز بولی `ready`. |

مقدارهای نامعتبر در سازنده با `ValueError` متوقف می‌شوند. تغییر تنظیمات، تعریف محصولی امتیاز را تغییر می‌دهد و بنابراین باید همراه با test fixture، ثبت نسخهٔ config در artifact بالادستی و بازبینی صاحب دامنه باشد.

## محاسبات و معنای خروجی

برای DataFrame غیرخالی، ماژول ابتدا شمارش missing در هر ستون را به‌دست می‌آورد. سپس فقط ستون‌های non-numeric را برای high cardinality بررسی می‌کند و nullها را از صورت و مخرج کنار می‌گذارد. برای ستون‌های numeric، تبدیل عددی، حذف nullها و سپس `numpy.isfinite` انجام می‌شود؛ بنابراین `NaN` در missingness منعکس می‌شود و `+∞` یا `-∞` در شمارش non-finite ظاهر می‌شوند.

اگر یک ستون حداقل `minimum_numeric_observations` مقدار finite داشته باشد، چارک‌های ۲۵٪ و ۷۵٪ محاسبه می‌شوند. وقتی `IQR = Q3 - Q1` صفر یا non-finite نباشد، مقدارهای بیرون از بازهٔ زیر outlier سلولی هستند:

```text
lower_bound = Q1 - iqr_multiplier × IQR
upper_bound = Q3 + iqr_multiplier × IQR
```

امتیاز به‌صورت زیر محاسبه می‌شود. `ceil` و سقف هر جریمه بخشی از قرارداد رفتاری فعلی هستند:

```text
missing_penalty    = min(40, ceil(missing_cell_ratio × 100))
identifier_penalty = min(20, 5 × high_cardinality_column_count)
outlier_penalty    = min(30, ceil(outlier_cell_ratio × 100))
non_finite_penalty = min(20, ceil(100 × non_finite_cells / max(rows, 1)))

readiness_score = max(0, 100 - مجموع جریمه‌ها)
ready = readiness_score >= readiness_threshold
```

نسبت outlier با `finite_numeric_observations` محاسبه می‌شود؛ نه کل سلول‌ها. در نتیجه، این امتیاز یک ابزار triage برای دادهٔ تحلیلی است و برای مقایسهٔ مستقیم datasetهای با ساختار بسیار متفاوت مناسب نیست.

| کلید `summary` برای DataFrame غیرخالی | نوع | معنا |
|---|---|---|
| `ready` | `bool` | مقایسهٔ امتیاز با `readiness_threshold`. |
| `rows`، `columns` | `int` | شکل DataFrame فعال. |
| `numeric_columns` | `int` | شمار ستون‌هایی که pandas numeric تشخیص داده است. |
| `numeric_columns_considered` | `int` | ستون‌های numeric دارای دادهٔ finite کافی و IQR قابل‌محاسبه. |
| `finite_numeric_observations` | `int` | کل مشاهده‌های finite numeric پیش از filter حداقل مشاهده. |
| `columns_with_missing`، `missing_cells` | `int` | شمار ستون‌های دارای null و کل سلول‌های null. |
| `missing_cell_ratio` | `float` | نسبت missing به `rows × columns`، با گردکردن تا شش رقم اعشار. |
| `high_cardinality_columns` | `int` | شمار ستون‌های non-numeric مشکوک به identifier. |
| `non_finite_numeric_cells` | `int` | تعداد `+∞` و `-∞` مشاهده‌شده در ستون‌های numeric. |
| `outlier_cells` | `int` | شمار مشاهده‌های finite بیرون از کران‌های IQR. |
| `readiness_score` | `int` | امتیاز heuristic در بازهٔ `0..100`. |

هشدارها به ترتیب ثابت missingness، high-cardinality، non-finite و outlier تولید می‌شوند. متن هشدار ممکن است **نام ستون** و شمارش تجمیعی را داشته باشد، اما نباید مقادیر سلول، مسیر فایل، نام فایل، ایمیل، کلید یا شناسهٔ شخصی در آن تزریق شود. اگر نام ستون خودش حساس است، لایهٔ بالاتر باید پیش از اشتراک‌گذاری artifact آن را pseudonymize یا report را local نگه دارد.

### حالت DataFrame خالی

DataFrame بدون ردیف یک مسیر اختصاصی دارد:

```python
ProcessingResult(
    module_id="data-readiness-insights/v1",
    summary={"ready": False, "rows": 0, "columns": column_count},
    warnings=("The active dataset has no rows to analyze.",),
)
```

این مسیر عمداً کلید `readiness_score` ندارد. مصرف‌کننده باید برای dataset خالی به `ready=False` و هشدار تکیه کند؛ گزارش‌دهی خودکار استاندارد نیز برای این مورد باید پیش از مصرف score، سیاست صریح خود داشته باشد. در پیاده‌سازی فعلی `AutomatedReportService` گزارش خودکار با score اجباری را برای DataFrame خالی رد می‌کند تا artifact گمراه‌کننده نسازد.

## تضمین‌های قابل‌اتکا و محدودیت‌ها

با یک DataFrame، config و نسخهٔ dependency یکسان، ترتیب هشدارها و شمارش‌های ماژول deterministic هستند. ماژول روی ورودی assignment انجام نمی‌دهد و test suite تغییرنکردن frame را بررسی می‌کند. بااین‌حال، deterministic بودن معادل درستی حوزه‌ای نیست: نسخهٔ pandas/NumPy، semantics dtype، و انتخاب ایدهٔ IQR می‌توانند interpretation را تغییر دهند.

| تضمین فعلی | محدودیت مهم |
|---|---|
| پردازش local-only و بدون I/O شبکه | تضمین جلوگیری از خروج همهٔ داده‌ها فقط با architecture کل برنامه حاصل می‌شود، نه با این کلاس به‌تنهایی. |
| خروجی aggregate-only | نام ستون‌ها ممکن است حساس باشند؛ raw values نیستند اما باید با طبقه‌بندی داده سازگار باشند. |
| تشخیص non-finite و IQR | outlier لزوماً خطا نیست و دادهٔ فصلی، heavy-tail یا regime-change ممکن است هشدار معتبر ولی غیرقابل‌اقدام ایجاد کند. |
| high-cardinality غیرعددی | identifier بودن یک فرض heuristic است؛ categoryهای مشروع پرتنوع می‌توانند flag شوند. |
| `ready` و score | معیار پذیرش کسب‌وکاری یا کنترل انطباق نیست. قرارداد کیفیت برای policyهای blocking باید جداگانه اجرا شود. |

## اتصال به UI، کیفیت و گزارش‌دهی

UI نباید منطق pandas، فرمول امتیاز یا string-formatting قابل‌استفادهٔ مجدد را بازپیاده‌سازی کند. `app/composition.py` وابستگی‌ها را می‌سازد و UI فقط `process(frame, ProcessingContext())` را orchestration می‌کند. `DataContract.evaluate()` و `DataReadinessInsightsModule.process()` دو ابزار مستقل‌اند: اولی قواعد policy مانند `not_null` و `unique` را ارزیابی می‌کند؛ دومی diagnostics توصیفی می‌دهد.

`AutomatedReportService` فقط `DatasetProfile`، `ProcessingResult` از همین module_id و `QualityReport` اختیاری را می‌پذیرد؛ DataFrame قبول نمی‌کند. بنابراین HTML و manifest تنها شامل دادهٔ تجمیعی هستند. گزارش خودکار محلی می‌تواند وضعیت `quality=blocked` را **نمایش دهد**؛ اما گزارش verified همچنان فقط از `VerifiedExportService` و quality gate عبور می‌کند. این جداسازی از ارائهٔ یک گزارش عادی به‌عنوان گواهی اعتماد جلوگیری می‌کند.

## الگوی توسعه و آزمون

برای افزودن یک diagnostic جدید، ابتدا معنای محصولی، دادهٔ لازم، اثر privacy و معیار پذیرش را مشخص کنید. سپس summary key جدید را version-safe اضافه کنید، با test fixture هم برای حالت سالم و هم edge case پوشش دهید و سازگاری report consumerها را بررسی کنید. کلیدهای موجود را حذف یا semantic آن‌ها را در همان `v1` تغییر ندهید؛ برای breaking change module_id جدید بسازید.

```python
import pandas as pd
from core.analysis.contracts import ProcessingContext
from core.analysis.data_readiness import DataReadinessInsightsModule

frame = pd.DataFrame({"amount": [10.0, 12.0, float("inf"), 900.0], "segment": ["a", "b", "c", None]})
result = DataReadinessInsightsModule().process(frame, ProcessingContext(locale="fa-IR"))
assert result.module_id == "data-readiness-insights/v1"
assert result.summary["rows"] == 4
assert result.summary["non_finite_numeric_cells"] == 1
```

پیش از merge، حداقل فرمان زیر را اجرا کنید. اجرای offscreen برای آزمون‌های PyQt در CI محلی ضروری است:

```bash
cd nextgen
QT_QPA_PLATFORM=offscreen pytest
python -m py_compile core/analysis/data_readiness.py core/reporting/automated_report.py
```

علاوه بر آزمون unit، برای هر توسعهٔ جدید این سناریوها را پوشش دهید: DataFrame خالی، نام ستون تکراری، all-null numeric، `+∞`/`-∞`، IQR صفر، دادهٔ با نسبت missing بالا، high-cardinality مشروع، immutable input، ترتیب determinism و عدم‌وجود raw value/source path در artifact گزارش.

## چک‌لیست بازبینی تغییرات

هر تغییر باید نشان دهد که خروجی فقط aggregate است، warningها مقدار سلول ندارند، score همچنان به‌عنوان heuristic برچسب خورده، policy blocking از `DataContract` جداست، و یک artifact محلی نمی‌تواند به اشتباه verified/signed خوانده شود. هر پیشنهاد برای پیش‌بینی، ریسک مالی، anomaly model، causal inference یا automated decision باید یک ADR جدا، دادهٔ test مجاز، ارزیابی bias/leakage، model card، validation زمان‌محور و بازبینی انسانی داشته باشد.
