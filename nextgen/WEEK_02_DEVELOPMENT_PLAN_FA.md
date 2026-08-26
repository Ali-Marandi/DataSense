# برنامهٔ توسعهٔ هفتهٔ دوم DataSense

**بازه:** روزهای ۸ تا ۱۴ توسعه  
**هدف هفته:** تبدیل Alpha از یک shell قابل‌اعتماد اولیه به یک نسخهٔ قابل‌مشاهده‌تر و قابل‌پشتیبانی‌تر، با تحلیل آمادگی داده، logging محلی، error monitoring و مستندات کاربر.

> **اصل اولویت‌بندی:** در هفتهٔ دوم، قابلیت‌هایی اجرا می‌شوند که کیفیت داده، مشاهده‌پذیری و تجربهٔ آزمایشی را بهتر می‌کنند. اتصال broker، سفارش‌گذاری، توصیهٔ سرمایه‌گذاری، ارسال خودکار داده یا مدل‌های مالی black-box خارج از محدوده‌اند.

## ۱. تعریف موفقیت هفته

| محور | خروجی قابل‌سنجش | معیار پذیرش |
|---|---|---|
| تحلیل | `DataReadinessInsightsModule` و اتصال UI | نمایش aggregate readiness بدون data leak و حداقل سه آزمون unit |
| قابلیت مشاهده | JSONL rotating log و `errors.jsonl` محلی | خطای ثبت‌شده error ID دارد و مسیر/email در آزمون redaction نمی‌ماند |
| تجربه Alpha | راهنمای کاربر فارسی و مسیرهای UI قابل‌توضیح | کاربر جدید بتواند import، validate، insight و verified export را انجام دهد |
| کیفیت | test suite کامل و check نحوی | همهٔ تست‌ها سبز و import/UI headless قابل‌اجرا |
| انتشار | branch تمیز، commitهای مستقل و CI آماده | workflow Windows بر روی branch اجراپذیر باشد |

## ۲. برنامهٔ روزانه

### روز ۸ — تثبیت baseline و تعریف قرارداد insight

روز نخست با مرور commitهای Alpha، خروجی CI ویندوز و محدودیت‌های privacy آغاز می‌شود. قرارداد `ProcessingModule`، `ProcessingContext` و `ProcessingResult` باید مرز تنها برای همهٔ تحلیل‌های آینده باشند. برای module جدید یک RFC کوچک در issue یا PR description ثبت کنید: هدف توصیفی، دادهٔ ورودی، aggregate خروجی، warningها و مواردی که module عمداً انجام نمی‌دهد.

| تسک | فایل/ناحیه | خروجی | معیار پذیرش |
|---|---|---|---|
| مرور baseline | `nextgen/tests/` و workflow | فهرست ریسک regression | test suite baseline سبز است |
| تعریف score | `core/analysis/data_readiness.py` | config immutable برای IQR/cardinality | validation همهٔ پارامترها را رد یا قبول می‌کند |
| مدل privacy | RFC/PR | ممنوعیت raw value در summary/warning | نمونهٔ خروجی فقط aggregate دارد |
| commit پیشنهادی | — | `docs: define week two readiness module contract` | تغییر کوچک و قابل review |

### روز ۹ — پیاده‌سازی تحلیل آمادگی داده

در این روز منطق readiness پیاده می‌شود: completeness ستون‌ها، identifier احتمالی بر اساس high-cardinality غیرعددی و outlierهای robust مبتنی بر IQR. module نباید DataFrame را mutate کند، نباید مقدار outlier را در warning بنویسد و نباید به UI یا telemetry وابسته باشد.

| تسک | فایل/ناحیه | خروجی | معیار پذیرش |
|---|---|---|---|
| پیاده‌سازی config | `core/analysis/data_readiness.py` | `DataReadinessConfig` immutable | مقدار غیرمجاز با `ValueError` رد می‌شود |
| پیاده‌سازی diagnostics | همان فایل | score، count و warning aggregate | input سالم score ۱۰۰ می‌گیرد |
| handling خالی | همان فایل | result ساختاریافته، نه crash | DataFrame خالی warning قابل‌اقدام دارد |
| commit پیشنهادی | — | `feat(analysis): add local data readiness insights` | unit test پایه افزوده شده است |

### روز ۱۰ — آزمون و اتصال insight به UI

این روز برای جلوگیری از coupling انجام می‌شود. UI فقط `ProcessingResult` را render می‌کند و data-cell را نمایش نمی‌دهد. دکمهٔ toolbar و فضای **Prepare & Validate** باید یک مسیر مشترک داشته باشند.

| تسک | فایل/ناحیه | خروجی | معیار پذیرش |
|---|---|---|---|
| unit test | `tests/test_data_readiness.py` | happy path، missing، outlier، invalid config | coverage همهٔ branchهای حساس را می‌بیند |
| UI binding | `ui/main_window.py` | دکمه و `insights_view` | sample flow readiness text دارد |
| privacy regression | `tests/test_readiness_ui.py` | نبود sample value در output | `SO-1001` یا مقدار outlier در view نیست |
| commit پیشنهادی | — | `feat(ui): expose local readiness insights` | headless UI test سبز است |

### روز ۱۱ — logging ساختاریافته و redaction

در روز یازدهم، log text ساده با JSONL قابل‌پردازش جایگزین می‌شود. rotating file handler باید حجم را محدود کند و formatter باید timestamp، level، logger و message redacted بسازد. هر log domain باید count، status و identifier عملیاتی بی‌خطر داشته باشد، نه path یا raw cell.

| تسک | فایل/ناحیه | خروجی | معیار پذیرش |
|---|---|---|---|
| formatter | `app/observability.py` | `JsonLineFormatter` | هر line JSON معتبر است |
| redaction | همان فایل | حذف email و pathهای رایج | test حاوی path/email عبور می‌کند |
| rotation | همان فایل | `RotatingFileHandler` | حداکثر ۵ backup محلی نگه داشته می‌شود |
| bootstrap | `app/bootstrap.py` | نصب logger هنگام startup | startup headless همچنان کار می‌کند |
| commit پیشنهادی | — | `feat(obs): add redacted rotating local logs` | log برای operation نمونه نوشته می‌شود |

### روز ۱۲ — error monitoring و ارتباط با UI

در روز دوازدهم، تمام خطاهای قابل‌پیش‌بینی UI حداقل در import CSV، readiness، verified export و receipt verification به `LocalErrorMonitor` متصل می‌شوند. کاربر به‌جای traceback یک `Error reference` می‌بیند؛ توسعه‌دهنده می‌تواند همان شناسه را در `errors.jsonl` دنبال کند.

| تسک | فایل/ناحیه | خروجی | معیار پذیرش |
|---|---|---|---|
| error record | `app/observability.py` | schema نسخه‌دار و UUID | record شامل error type و context redacted است |
| injection | `app/composition.py` | `Observability` در `Services` | UI از singleton پنهان استفاده نمی‌کند |
| UI handling | `ui/main_window.py` | پیام کاربرپسند و logging | failure باعث crash پنجره نمی‌شود |
| tests | `tests/test_observability.py` | error/log redaction test | raw path/email در فایل test نیست |
| commit پیشنهادی | — | `feat(obs): add local error references for UI failures` | unit suite سبز است |

### روز ۱۳ — راهنمای کاربر و سناریوی پذیرش Alpha

راهنما باید یک کاربر غیرتوسعه‌دهنده را از download تا receipt verification هدایت کند. به‌ویژه لازم است محدودیت unsigned build، checksum، local-only behavior، مفهوم quality blocking و محدودیت score آمادگی داده به‌روشنی توضیح داده شوند.

| تسک | فایل/ناحیه | خروجی | معیار پذیرش |
|---|---|---|---|
| راهنما | `USER_GUIDE_ALPHA_FA.md` | سناریوی کامل استفاده | یک همکار می‌تواند بدون کمک توسعه‌دهنده مسیر را اجرا کند |
| troubleshooting | همان فایل | جدول نشانه/علت/راه‌حل | import/export/receipt/error reference پوشش دارند |
| release note | `CHANGELOG` یا PR description | تغییرهای کاربرمحور | هشدار unsigned حذف نشده است |
| commit پیشنهادی | — | `docs: add Alpha user guide and support workflow` | لینک‌ها و نام دکمه‌ها صحیح‌اند |

### روز ۱۴ — hardening، release rehearsal و retrospective

روز آخر فقط برای افزایش قابلیت اعتماد است، نه افزودن feature جدید. test، py_compile، workflow validation، smoke test headless و بررسی log hygiene اجرا می‌شوند. سپس یک retrospective کوتاه از آنچه کار کرد، مانع‌ها و اولویت هفتهٔ سوم نوشته می‌شود.

| تسک | فرمان/فایل | خروجی | معیار پذیرش |
|---|---|---|---|
| تست کامل | `QT_QPA_PLATFORM=offscreen pytest` | گزارش سبز | هیچ regression باز وجود ندارد |
| syntax | `python -m py_compile` روی moduleها | check نحوی | import error ندارد |
| CI review | `.github/workflows/nextgen-windows-release.yml` | asset pattern و unsigned notice | artifact داخلی PyInstaller منتشر نمی‌شود |
| log hygiene | `tests/test_observability.py` | redaction review | path/email/raw sample در test output نیست |
| retrospective | `docs/week-02-retrospective.md` | ریسک و اولویت هفته ۳ | owner و next action مشخص است |

## ۳. گردش کنترل کیفیت روزانه

در پایان هر روز، توسعه‌دهنده باید تغییرات را به یک commit کوچک، تک‌منظوره و قابل rollback محدود کند. قبل از push، `pytest` در headless mode، `git diff --check` و بررسی عدم ورود `dist/`، `build/`، logها، keyها و datasetهای واقعی به commit ضروری است. PR باید حداقل یک سناریوی happy path، یک سناریوی failure و یک ملاحظهٔ privacy را شرح دهد.

| کنترل | مالک | حداقل معیار |
|---|---|---|
| Unit/UI tests | توسعه‌دهنده | همه سبز |
| Privacy review | توسعه‌دهنده + reviewer | نبود raw value/path/secret در artifact و log |
| Workflow review | توسعه‌دهنده | build/release asset pattern محدود است |
| User-doc review | product/QA | متن با UI واقعی منطبق است |
| Release decision | owner محصول | Alpha/unsigned notice صریح است |

## ۴. اولویت‌های هفتهٔ سوم پس از خروجی این هفته

هفتهٔ سوم باید به UI پروژه‌ها (`.dsproj` open/save)، انتخاب contract، فیلتر/جست‌وجوی profile، بهبود accessibility، به‌روزرسانی provider امضای محلی و بررسی installer production بپردازد. مدل‌های پیشرفتهٔ مالی یا ML فقط پس از تثبیت data lineage، testهای time-integrity و review مستقل model risk وارد backlog اجرایی می‌شوند.

> این برنامهٔ توسعه یک طرح فنی محصول است. ماژول آمادگی داده فقط diagnostics توصیفی ارائه می‌دهد و نباید به‌عنوان توصیهٔ مالی یا تصمیم سرمایه‌گذاری استفاده شود.
