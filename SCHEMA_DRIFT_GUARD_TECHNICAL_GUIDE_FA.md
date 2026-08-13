# گزارش فنی Schema Drift Guard در DataSense

## هدف و محدوده

**Schema Drift Guard** یک کنترل data-observability در Trust Center است که ساختار dataset فعلی را با ساختار تأییدشدهٔ قبلی مقایسه می‌کند. این قابلیت برای تشخیص زودهنگام تغییرهای upstream طراحی شده است؛ برای مثال، زمانی که ستونی حذف یا افزوده شده، نوع یک ستون تغییر کرده، ستونی که قبلاً کامل بوده اکنون دارای مقدار تهی شده یا ترتیب ستون‌ها تغییر کرده است.

> این کنترل، **کیفیت مقدارها** را جایگزین نمی‌کند و DataFrame را اصلاح یا حذف نمی‌کند. وظیفهٔ آن تولید evidence ساختاری و اعمال policy سازگاری پیش از اتکا به تحلیل، export یا release است.

دلیل طراحی این قابلیت، تفکیک صریح **تغییر schema** از **تغییر کیفیت داده** است. قراردادهای داده در معماری‌های بالغ علاوه بر structure، integrity constraint، metadata، policy و schema evolution را پوشش می‌دهند.[1] Schema drift نیز به تغییرهای ناخواستهٔ ساختار مانند افزودن، حذف یا تغییر ستون/type گفته می‌شود که می‌توانند گزارش‌ها و سامانه‌های downstream را ناسازگار کنند.[2]

## مدل داده و حریم خصوصی

Baseline به‌صورت `SchemaSnapshot` در `core/governance.py` نگهداری می‌شود. هر entry فقط سه attribute دارد: نام ستون، نمایش رشته‌ای `pandas dtype` و یک boolean با نام `nullable`. مقدار `nullable=True` فقط نشان می‌دهد که حداقل یک مقدار تهی در ستون وجود دارد. این snapshot **مقدار هیچ سلول، sample، PII یا row-level metadata** را ذخیره نمی‌کند.

| جزء | مسئولیت | دادهٔ نگهداری‌شده | دادهٔ نگهداری‌نشده |
|---|---|---|---|
| `SchemaSnapshot` | baseline نسخه‌دار ساختار | `(column_name, dtype, nullable)` و timestamp | مقدار سلول، نمونه، hash مقدار، PII خام |
| `fingerprint` | شناسهٔ قابل‌ردیابی baseline/current | SHA-256 از JSON canonical ستون‌ها | secret، کلید امضا یا محتوای dataset |
| `SchemaDriftPolicy` | تعیین compatibility | پنج flag policy و نام policy | rule value یا اطلاعات کاربر |
| `SchemaDriftReport` | evidence تصمیم | diff ساختاری، fingerprintها، reasons و decision | rowهای ناقض یا مقدارهای حساس |

Fingerprint با SHA-256 از JSON پایدار شامل tupleهای schema محاسبه می‌شود. بنابراین اگر نام ستون، type، nullable یا ترتیب ساختار تغییر کند، fingerprint نیز تغییر خواهد کرد. Fingerprint برای correlation و audit مفید است، اما **امضای رمزنگارانهٔ evidence** نیست؛ امضای KMS/HMAC، به‌عنوان مرحلهٔ بعدی roadmap، برای اثبات tamper-evidence در سطح enterprise لازم است.

## Policy پیش‌فرض و منطق سازگاری

Policy پیش‌فرض با نام `Default schema compatibility policy` به گونه‌ای تنظیم شده است که تغییرهای کم‌خطر additive را بپذیرد، اما تغییرهای بالقوه breaking را block کند.

| تغییر تشخیص‌داده‌شده | flag policy | پیش‌فرض | تصمیم پیش‌فرض | منطق تجاری |
|---|---|---:|---|---|
| افزودن ستون | `allow_added_columns` | `True` | Compatible | consumerهای tolerant معمولاً می‌توانند ستون اضافه را نادیده بگیرند. |
| حذف ستون | `allow_removed_columns` | `False` | Blocked | dashboard/model downstream ممکن است به ستون حذف‌شده وابسته باشد. |
| تغییر dtype | `allow_dtype_changes` | `False` | Blocked | تبدیل `string→int` یا `int→float` می‌تواند semantics و queryها را بشکند. |
| nullable شدن ستون قبلاً non-null | `allow_nullability_relaxation` | `False` | Blocked | indicator کامل بودن داده ضعیف می‌شود و downstream ممکن است failure داشته باشد. |
| تغییر ترتیب ستون‌های مشترک | `allow_column_reordering` | `True` | Compatible | بیشتر عملیات dataframe نام‌محورند، اما policy سخت‌گیر می‌تواند آن را block کند. |

Policy قابل‌سریال‌سازی است و با `SchemaDriftPolicy.to_dict()` در پروژه نگهداری می‌شود. در نتیجه، تیم مالک داده می‌تواند برای یک dataset حساس policy سخت‌گیرانه‌تر اعمال کند، بدون اینکه رفتار همهٔ پروژه‌ها تغییر کند.

## الگوریتم تصمیم

هنگام approval، متد `capture_schema(frame)` روی DataFrame موجود اجرا و snapshot ایجاد می‌شود. هنگام بررسی، `compare_schema(baseline, frame, policy)` همان snapshot ساختاری را از DataFrame فعلی می‌گیرد و mapهای expected/current می‌سازد.

| مرحله | عملیات | خروجی |
|---:|---|---|
| 1 | بررسی وجود baseline و dataset جاری | در نبود هرکدام، `not configured` با reason شفاف |
| 2 | محاسبهٔ snapshot و fingerprint فعلی | metadata ساختاری بدون مقدار داده |
| 3 | مقایسهٔ نام ستون‌ها | `added_columns` و `removed_columns` |
| 4 | مقایسهٔ dtype برای ستون‌های مشترک | `dtype_changes` |
| 5 | مقایسهٔ non-null baseline با nullable current | `nullability_relaxations` |
| 6 | مقایسهٔ ترتیب ستون‌های مشترک | `column_order_changed` |
| 7 | ارزیابی هر diff در برابر flag policy | reasonهای قابل‌خواندن برای auditor |
| 8 | تولید decision | `blocked` اگر حداقل یک reason شامل نقض policy باشد؛ در غیر این صورت `compatible` |

برای مثال، baseline زیر را در نظر بگیرید:

```text
customer_id: string, nullable=False
amount: int64, nullable=False
```

اگر dataset جدید شامل `customer_id: int64`، `amount: float64` با یک مقدار null و ستون جدید `region` باشد، report به‌صورت زیر خواهد بود:

| فیلد report | مقدار |
|---|---|
| `added_columns` | `region` |
| `dtype_changes` | `customer_id`, `amount` |
| `nullability_relaxations` | `amount` |
| `decision` | `blocked` |
| دلیل | dtype و nullability با policy پیش‌فرض ناسازگارند؛ ستون جدید به‌تنهایی مجاز است. |

## یکپارچه‌سازی با DataSense

`DataManager` سه state جدید دارد: `schema_baseline`، `schema_drift_policy` و متدهای `set_schema_baseline()`، `set_schema_drift_policy()` و `check_schema_drift()`. هنگام بارگذاری dataset جدید، baseline و policy در سطح dataset reset می‌شوند تا schema dataset قبلی به‌اشتباه به فایل جدید اعمال نشود.

فایل پروژهٔ `.dsproj` در manifest، baseline و policy را در کنار قرارداد کیفیت، Quality Gate و history ذخیره می‌کند. پس از `load_project` همان policy و snapshot دوباره hydrate می‌شوند و report جدید روی dataset بازیابی‌شده قابل‌محاسبه است. در Trust Center دو action افزوده شده‌اند: **Approve current schema** برای ایجاد baseline و **Check schema drift** برای نمایش decision/reasons. کارت summary با عنوان **Schema guard** نیز آخرین وضعیت را نشان می‌دهد. Export audit، baseline، policy و report فعلی schema drift را در evidence JSON قرار می‌دهد.

## گردش کار پیشنهادی برای تیم داده

ابتدا dataset مورد اعتماد را باز کنید و قرارداد کیفیت را اجرا کنید. پس از بازبینی owner، از **Approve current schema** استفاده کنید؛ این عمل باید به‌عنوان approval عملیاتی تیم ثبت شود، نه صرفاً یک کلیک فنی. در هر import جدید، transform عمده یا پیش از export حساس، **Check schema drift** را اجرا کنید. اگر وضعیت `compatible` بود، evidence همچنان نشان می‌دهد چه تغییر مجازی رخ داده است. اگر `blocked` بود، dataset را به baseline برنگردانید؛ ابتدا upstream contract، migration و policy را بررسی کنید، سپس در صورت تصمیم آگاهانهٔ owner یک baseline جدید approve کنید.

برای داده‌های حساس، baseline update باید با change ticket، reviewer مستقل و دلیل business همراه باشد. برای جلوگیری از «approval به‌منظور عبور دادن drift»، می‌توان در Control Plane آینده approval را با RBAC، two-person rule و signed evidence bundle اجباری کرد.

## ارتباط با Quality Gate

Schema Drift Guard و Quality Gate دو کنترل مستقل هستند. Quality Gate نتیجهٔ ruleهای کیفیت داده را با score، critical/high failure و execution error ارزیابی می‌کند. Schema Drift Guard سازگاری ساختاری میان baseline و DataFrame جاری را ارزیابی می‌کند. در نسخهٔ فعلی، report schema drift در audit export ثبت می‌شود و در UI نمایش داده می‌شود؛ gate کیفیت به‌طور خودکار decision schema drift را در score ادغام نمی‌کند. این تفکیک عمدی است تا تغییرهای ساختاری با کیفیت value-level مخلوط نشوند. گام بعدی product می‌تواند یک **release gate مرکب** باشد که Quality Gate و Schema Guard را با policy صریح سازمانی ترکیب کند.

## آزمون و شواهد

دو آزمون افزوده شده‌اند. نخست، تغییر dtype و nullable شدن `amount` همراه با ستون `region` را بررسی می‌کند و باید `blocked` شود؛ همچنین تأیید می‌کند evidence baseline مقدارهای `'A'` و `'B'` را نگه نمی‌دارد. دوم، policy سخت‌گیرِ منع ستون جدید را در `.dsproj` ذخیره و بازیابی می‌کند و تصمیم blocked را پس از restore تأیید می‌نماید. مجموعهٔ کامل پس از این تغییر شامل **۷۹ آزمون موفق** و دو warning غیرمسدودکنندهٔ joblib بوده است.

## محدودیت‌های آگاهانه و مسیر production

نسخهٔ فعلی nullable را از وجود حداقل یک null در DataFrame استخراج می‌کند؛ بنابراین nullable در اینجا یک property مشاهده‌شده است نه declaration سطح database. Snapshot از pandas dtype استفاده می‌کند و semantic type مانند currency، timezone، enum یا precision decimal را هنوز مدل نمی‌کند. همچنین approvalها هنوز محلی‌اند و signed/tamper-evident نیستند. برای production enterprise، contract version، semantic schema، server-side approval، RBAC، audit retention، notification و signature مبتنی بر KMS باید به Control Plane متصل شوند.

## منابع

[1]: https://docs.confluent.io/cloud/current/sr/fundamentals/data-contracts.html "Confluent — Data Contracts for Schema Registry"
[2]: https://www.acceldata.io/blog/schema-drift "Acceldata — Understanding Schema Drift"
[3]: https://montecarlo.ai/blog-data-contracts-explained "Monte Carlo — Data Contracts 101"
