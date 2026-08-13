# شواهد فنی اجرای نهایی ۷۹ آزمون DataSense

## نتیجهٔ قابل‌تکرار

فرمان زیر از ریشهٔ مخزن اجرا شد و خروجی JUnit در `validation_evidence/full_suite_schema_drift.xml` ثبت گردید:

```bash
python3 -m pytest -q --junitxml=validation_evidence/full_suite_schema_drift.xml
```

JUnit suite نتیجهٔ `tests=79`، `failures=0`، `errors=0`، `skipped=0` و زمان `4.954s` را ثبت کرده است. تنها دو warning غیرمسدودکننده از `joblib.numpy_pickle` در test مدل (deprecation تغییر shape آرایه در NumPy 2.5) وجود دارد. هیچ test شکست‌خورده، error یا skipped در evidence نهایی ثبت نشده است.

> عدد **۷۰** به اجرای هدفمند زمان انتشار اشاره دارد. عدد **۷۹** اجرای کامل فعلی است: ۷۷ test پس از تثبیت headless PyQt، به‌علاوهٔ دو test جدید Schema Drift Guard.

## توزیع suite

| ماژول آزمون | تعداد | پوشش فنی |
|---|---:|---|
| `tests.test_v2_1_engines` | 53 | APIهای DataManager، import/export، transform، undo/redo، profiling، SQL safe-select، forecast/model، dashboard و engineهای v2.1. |
| `tests.test_governance` | 12 | قرارداد داده، score/gate، PII-safe scan، history، persistence، Schema Drift Guard و policy. |
| `tests.test_import_smoke` | 7 | import workspaceهای desktop و launch/close ایمن `MainWindow` با Trust Center. |
| `enterprise_control_plane.tests.test_security_flow` | 4 | PKCE authorization code، tenant boundary/audit و SAML replay/strict configuration. |
| `tests.test_data_manager` | 3 | رفتار پایهٔ DataManager و سازگاری عملیات داده. |
| **کل** | **79** | **بدون failure/error/skipped** |

## سناریوهای Schema Drift Guard

### ۱. تغییر breaking در dtype و nullability بدون نگهداری مقدار داده

Case: `test_schema_drift_blocks_breaking_dtype_and_nullability_changes_without_retaining_values`

این case از یک baseline با `customer_id: string, non-null` و `amount: int, non-null` آغاز می‌کند. سپس dataset جدید `customer_id` را به integer تبدیل می‌کند، `amount` را nullable/float می‌سازد و ستون جدید `region` اضافه می‌کند. نتیجهٔ مورد انتظار و ثبت‌شده چنین است:

| property report | نتیجه |
|---|---|
| `decision` | `blocked` |
| `added_columns` | `region` |
| `dtype_changes` | `customer_id` و `amount` |
| `nullability_relaxations` | `amount` |
| privacy assertion | مقدارهای نمونهٔ `A` و `B` در baseline evidence وجود ندارند. |

این test ثابت می‌کند که افزوده‌شدن ستون، مطابق policy پیش‌فرض، به‌تنهایی می‌تواند compatible باشد؛ اما تغییر type و ضعیف‌شدن non-null constraint، که breaking تلقی می‌شوند، decision را block می‌کنند. همچنین test تأیید می‌کند snapshot فقط metadata ساختاری دارد و row values را نگه نمی‌دارد.

### ۲. policy سخت‌گیر و ماندگاری در `.dsproj`

Case: `test_schema_drift_policy_can_reject_additive_columns_and_persists_with_project`

در این سناریو، policy با نام `Strict schema` و `allow_added_columns=False` تعریف می‌شود. اضافه‌شدن ستون `country` باید blocked شود. سپس پروژه با `save_project` ذخیره و توسط `load_project` بازیابی می‌گردد. baseline و policy باید بازگردند و decision schema drift همچنان `blocked` بماند. این test ثابت می‌کند policy در سطح پروژه پایدار است و قرار نیست با بازشدن مجدد پروژه به پیش‌فرض permissive برگردد.

## کنترل‌های Trust Center و Quality Gate

دوازده case governance، کنترل‌های زیر را پوشش می‌دهند: اجرای rule بدون mutate کردن DataFrame؛ امتیاز ندادن کاذب به قرارداد خالی؛ JSON portability قرارداد؛ عدم ذخیرهٔ value در PII findings؛ پیشنهاد ruleهای محافظه‌کارانه؛ باطل‌شدن report پس از mutation؛ persistence قرارداد؛ Quality Gate برای score پایین/critical failure؛ trend/history privacy-safe؛ persistence policy/history؛ و دو case Schema Drift بالا.

Quality Gate مستقل از Schema Drift Guard است. Quality Gate کیفیت ruleهای value-level را با score، severity و error بررسی می‌کند، اما Schema Drift Guard سازگاری ساختاری current dataset با baseline را بررسی می‌نماید. هر دو در evidence قابل‌صادرات هستند، ولی score quality به‌طور خودکار schema decision را در خود ادغام نمی‌کند.

## کنترل‌های امنیت سازمانی

| Case | اثبات |
|---|---|
| `test_authorization_code_requires_matching_pkce_and_is_single_use` | authorization code فقط با PKCE verifier سازگار قابل‌مصرف است و reuse رد می‌شود. |
| `test_authorization_code_rejects_wrong_pkce_verifier` | verifier نادرست نمی‌تواند code را به token تبدیل کند. |
| `test_permission_service_hides_cross_tenant_resource_and_audits_denial` | دسترسی cross-tenant پنهان و deny در audit ثبت می‌شود. |
| `test_saml_acs_uses_strict_toolkit_configuration_and_rejects_assertion_replay` | تنظیم strict SAML و جلوگیری از replay assertion فعال است. |

این‌ها unit/security-flow testهای کنترل‌پلین هستند، نه جایگزین integration test با IdP واقعی، penetration test، threat model یا production certification.

## پایداری PyQt و smoke tests

هفت test import/smoke، import ماژول‌های UI و ساخت/بستن `MainWindow` را ارزیابی می‌کنند. برای runnerهای Linux headless، `conftest.py` پیش از importهای PyQt platform تست را به `offscreen` تنظیم می‌کند. این اصلاح باعث شد اجرای کامل `python3 -m pytest -q` بدون export دستی متغیر محیطی از native abort عبور کند. این bootstrap برای test است و behavior runtime desktop در Windows را تغییر نمی‌دهد.

## تفسیر عملی نتیجه

نتیجهٔ ۷۹ passed یک evidence قوی از regression suite فعلی است، اما معادل «تأیید production به تنهایی» نیست. انتشار production همچنان به Windows smoke روی artifact، code signing، dependency/security scan، release approval، monitoring، rollback plan و در بخش هویت، integration test با IdP staging نیاز دارد. 
