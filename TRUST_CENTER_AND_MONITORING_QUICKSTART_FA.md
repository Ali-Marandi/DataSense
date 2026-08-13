# راهنمای گام‌به‌گام Trust Center و مانیتورینگ DataSense

## هدف

Trust Center یک workspace محلی برای تعریف انتظارهای کیفیت، بازبینی signalهای حساسیت داده، تصمیم‌گیری Quality Gate، کنترل Schema Drift و نگهداری evidence پروژه است. این راهنما workflow عملی یک Data Steward یا analyst را از import تا export evidence توضیح می‌دهد. عملیات Trust Center دادهٔ اصلی را هنگام check تغییر نمی‌دهد؛ تغییرهای dataset فقط از actionهای جداگانهٔ workspaceهای تحولی انجام می‌شوند.

> **مرز مهم:** Schema Drift Guard و Data Lineage Tracker در desktop عملیاتی‌اند. سرویس مرکزی alerting برای Slack/Teams/Pager هنوز deploy نشده است؛ مسیر آماده‌سازی آن در بخش «مانیتورینگ مرکزی» آمده است.

## پیش‌نیاز

DataSense v2.2.1 یا build جدیدتر را در Windows اجرا کنید. یک فایل CSV، Excel، JSON، Parquet یا منبع پشتیبانی‌شده import نمایید و پیش از ورود به Trust Center مطمئن شوید جدول در workspace اصلی نمایش داده می‌شود. برای اجرای پروژه در CI/headless، test bootstrap مقدار platform Qt را به `offscreen` تنظیم می‌کند؛ این تنظیم لازم نیست در استفادهٔ معمول Windows انجام شود.

## گردش کار استاندارد

| گام | عمل در رابط | خروجی/تصمیم |
|---:|---|---|
| 1 | Dataset را import کنید و نوع/نام ستون‌ها را بازبینی نمایید. | یک project context با source مشخص ایجاد می‌شود. |
| 2 | workspace **Trust Center** را باز کنید. | دکمه‌های scan، quality check، schema baseline/check و lineage در دسترس‌اند. |
| 3 | روی **Scan sensitive data** کلیک کنید. | signalهای احتمالی PII به‌صورت metadata طبقه‌بندی می‌شوند؛ مقدار خام نگه‌داری نمی‌شود. |
| 4 | نام قرارداد را وارد کنید، ruleها را دستی اضافه کنید یا **Add recommended rules** را انتخاب نمایید. | Data Contract قابل‌مرور ساخته می‌شود. |
| 5 | روی **Run quality checks** کلیک کنید. | Quality Report، score، failed checks، Quality Gate و history به‌روز می‌شوند. |
| 6 | policy Quality Gate را متناسب با criticality داده تأیید کنید. | تصمیم `trusted`، `needs attention` یا `blocked` برای استفادهٔ بعدی مشخص می‌شود. |
| 7 | روی **Approve current schema** کلیک کنید، فقط پس از review مالک داده. | baseline ساختاری و بدون row value ثبت می‌شود. |
| 8 | پس از import/transform بعدی روی **Check schema drift** کلیک کنید. | سازگاری با baseline و reasonهای block/compatible نمایش داده می‌شود. |
| 9 | روی **View lineage** کلیک کنید. | حداکثر ۱۵ transformation آخر با زمان، row impact و تغییرهای ستونی بازبینی می‌شود. |
| 10 | پس از Run quality checks، از **Export audit JSON** استفاده کنید و سپس `.dsproj` را ذخیره نمایید. | evidence قابل‌اشتراک و state قابل‌بازیابی پروژه ایجاد می‌شود. |

## ساخت Data Contract با مثال

یک قرارداد فروش ماهانه می‌تواند ruleهای زیر را داشته باشد. ruleها انتظار داده را ثبت می‌کنند، نه این‌که داده را خودکار حذف یا اصلاح کنند.

| Rule | ستون نمونه | severity پیشنهادی | هدف |
|---|---|---|---|
| `not_null` | `order_id` | critical | شناسهٔ سطر نباید خالی باشد. |
| `unique` | `order_id` | critical | شناسهٔ سفارش نباید تکراری باشد. |
| `range` | `revenue` | high | درآمد باید داخل محدودهٔ معقول باشد. |
| `allowed_values` | `region` | medium | فقط منطقه‌های موردتأیید قابل‌پذیرش‌اند. |
| `freshness` | `loaded_at` | high | dataset نباید از حد مجاز قدیمی‌تر باشد. |

برای rule از نوع `range`، در فیلد Parameters JSON نمونهٔ زیر را وارد کنید:

```json
{"min": 0, "max": 1000000}
```

پس از اجرای check، هر rule یکی از سه وضعیت `pass`، `fail` یا `error` دارد. `error` بیانگر پیکربندی/اجرای ناموفق rule است و نباید با failure کیفیت داده یکی دانسته شود.

## تفسیر Quality Score و Gate

Quality Score با وزن severity ruleهای pass نسبت به ruleهای ارزیابی‌شده محاسبه می‌شود. وزن‌های محصول critical=4، high=3، medium=2 و low=1 هستند. score یک indicator است؛ Gate policy یک تصمیم مستقل است که minimum score، سقف failureهای critical/high و block-on-error را اعمال می‌کند.

اگر score بالا باشد اما یک `not_null` critical برای کلید اصلی fail شود، Gate باید به‌صورت `blocked` باقی بماند. برعکس، score پایین بدون failure critical می‌تواند به `needs attention` برسد، بسته به policy تعیین‌شده. در هر تصمیم release یا export حساس، Gate و failed checks را با هم بررسی کنید.

## راهنمای عملی Schema Drift Guard

### ثبت baseline

پس از آن‌که owner و Data Steward schema را تأیید کردند، **Approve current schema** را انتخاب کنید. baseline تنها نام ستون، dtype، nullability و fingerprint ساختاری را ثبت می‌کند. هرگز baseline را فقط برای حذف alert یا عبور از block تغییر ندهید؛ تغییر baseline باید یک change management record داشته باشد.

### تفسیر گزارش drift

| تغییر تشخیص‌داده‌شده | policy پیش‌فرض | واکنش پیشنهادی |
|---|---|---|
| ستون افزوده | compatible، مگر policy سخت‌گیر | بررسی consumerها و PII classification ستون جدید. |
| ستون حذف‌شده | blocked | dataset/downstream query را متوقف و impact analysis انجام دهید. |
| تغییر dtype | blocked | compatibility API/report/model را بررسی و مالک داده را مطلع کنید. |
| relaxed nullability | blocked | علت data-quality و اثر ruleهای not-null را بررسی کنید. |
| reordered columns | informative یا مطابق policy | برای consumerهای positional export بازبینی انجام دهید. |

پس از حل علت، یک check تازه اجرا کنید. فقط زمانی baseline جدید approve شود که change به‌صورت رسمی پذیرفته شده باشد.

## استفاده از Data Lineage Tracker

هر operation DataManager مانند rename، cast، drop column، duplicate cleanup، fill missing، undo و redo به event تبدیل می‌شود. **View lineage** برای پرسش‌هایی مانند «چه operationی schema را تغییر داد؟» یا «آیا row count پس از cleanup تغییر کرد؟» استفاده می‌شود. trail کامل همراه evidence JSON و `.dsproj` باقی می‌ماند، اما cell value یا PII خام را ذخیره نمی‌کند.

پیش از handoff پروژه، این سه مورد را بازبینی کنید: آخرین operation، تغییرهای added/removed/dtype و row count قبل/بعد. اگر event مشکوک است، از پروژه کپی بگیرید و با `Undo` یا reload از source اصلی، علت را بررسی کنید؛ evidence lineage را پاک نکنید.

## export و نگهداری evidence

برای export audit، ابتدا Quality Checks را اجرا کنید؛ export بدون Quality Report عمداً مجاز نیست. JSON نتیجه شامل contract، quality report، Gate decision، quality history، baseline/policy/report Schema Drift و `lineage` است. evidence باید در فضای ذخیره‌سازی کنترل‌شده با retention policy سازمان نگه‌داری شود. پیش از ارسال خارج از سازمان، policy طبقه‌بندی و sensitivity signalها را بازبینی کنید.

`.dsproj` قرارداد، policy/history کیفیت، baseline/policy schema و lineage را نگه می‌دارد. datasource قابل‌دسترسی و کنترل تغییر برای خود فایل پروژه باید جداگانه توسط سازمان مدیریت شود.

## مانیتورینگ مرکزی: وضعیت و مسیر عملیاتی

در نسخهٔ desktop، checkها local و کاربر-initiated هستند. برای استقرار سازمانی، سرویس مرکزی باید observation metadata-only را دریافت و policy/routing/audit را server-side انجام دهد.

| مرحله | پیاده‌سازی لازم | معیار خروج |
|---:|---|---|
| 1 | `SchemaObservation`، `SchemaDriftDecision` و policy versioned API | validation contract و tenant authorization test. |
| 2 | PostgreSQL برای datasets/policies/observations/incidents/outbox | transaction atomically decision + audit + outbox ثبت کند. |
| 3 | RBAC و service identity برای desktop/pipeline agent | request cross-tenant به 404/deny و audit تبدیل شود. |
| 4 | worker notification با dedupe، retry و DLQ | failure notification باعث گم‌شدن incident نشود. |
| 5 | Slack/Teams/email/SIEM/Pager route بر پایه severity/criticality | alert redacted، idempotent و قابل‌ack باشد. |
| 6 | metrics، dashboard و monitor-the-monitor | coverage، incident age، queue depth و delivery failure قابل‌مشاهده باشد. |
| 7 | pilot Tier-2 و سپس Tier-1 | evidence detection، owner ack و rollback ثبت شود. |

تا پیش از تکمیل این مراحل، هشدار عملیاتی را با export audit، review دوره‌ای، اجرای check پس از ingestion و workflow change management تیمی انجام دهید. دکمهٔ Schema Drift به‌تنهایی جایگزین incident management، on-call یا SIEM نیست.

## Runbook کوتاه برای drift `blocked`

در لحظهٔ مشاهدهٔ `blocked`، dataset را برای export/reporting حساس hold کنید. Report را export نمایید و نوع change را مشخص کنید. owner dataset و consumerهای شناخته‌شده را مطلع سازید. سپس علت upstream را برطرف یا contract/schema change را در ticket تأیید کنید. پس از check سازگار، evidence حل مسئله را به ticket پیوست کنید. baseline تازه فقط پس از approval رسمی ثبت شود.

## چک‌لیست استفادهٔ روزانه

| زمان | اقدام |
|---|---|
| پس از هر import یا refresh مهم | scan حساسیت، quality check و schema drift check. |
| پیش از export حساس یا گزارش مدیریتی | Gate decision، failed critical rules و latest lineage event. |
| پس از تغییر pipeline/schema | impact review، drift check، evidence export و approval. |
| هفتگی یا در cadence تیم | quality history/trend و incidentهای باز. |
| پیش از release سازمانی | suite آزمون، package smoke، audit evidence و production runbook. |
