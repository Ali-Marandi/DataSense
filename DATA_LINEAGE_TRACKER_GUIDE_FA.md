# قابلیت جدید: Data Lineage Tracker در DataSense

## ارزش تجاری

**Data Lineage Tracker** مسیر تغییرات dataset را در طول یک پروژهٔ DataSense به‌صورت یک trail قابل‌ممیزی ثبت می‌کند. هر transformation مهم مانند rename، cast، حذف ستون، cleaning، query، pivot، undo یا redo به یک رویداد تبدیل می‌شود. این قابلیت به analyst، Data Steward و auditor پاسخ می‌دهد که «این dataset چگونه به وضعیت فعلی رسیده است؟» و «کدام تغییر ستون، schema را دگرگون کرده است؟»

Lineage عملیاتی باید منشأ، transformation، وابستگی و context اجرا را ثبت کند تا تیم‌ها بتوانند root cause و impact change را سریع‌تر بررسی کنند.[1] lineage در سطح ستون برای fieldهای کلیدی، کنترل governance و تحلیل اثر تغییر schema ارزش بیشتری دارد.[2] پیاده‌سازی اولیهٔ DataSense با تمرکز روی provenance محلی و تغییر schema آغاز می‌شود و برای اتصال آینده به catalog/Control Plane آماده است.

## آنچه در نسخهٔ فعلی پیاده‌سازی شده است

| قابلیت | رفتار |
|---|---|
| ثبت خودکار mutation | `DataManager.set_frame` قبل/بعد هر mutation را ثبت می‌کند؛ بنابراین تمام operationsی که از مسیر مرکزی تغییر داده عبور می‌کنند، lineage دارند. |
| ثبت import | import dataset یک رویداد ریشه با source path و schema خروجی ایجاد می‌کند. |
| ثبت undo/redo | بازگشت و اجرای مجدد تغییر نیز event مستقل دارند و مسیر تصمیم analyst را شفاف می‌کنند. |
| snapshot بدون مقدار داده | هر event فقط schema، تعداد ردیف، نام operation، زمان UTC، source و fingerprint دارد؛ هیچ cell value یا sample PII ذخیره نمی‌شود. |
| تغییرهای ستونی | ستون افزوده/حذف‌شده و dtypeهای تغییرکرده از schema قبل/بعد استخراج می‌شوند. |
| persistence | trail با `.dsproj` ذخیره و هنگام بازکردن پروژه بازیابی می‌شود. |
| Trust Center | دکمهٔ **View lineage** حداکثر ۱۵ رویداد آخر را با operation، زمان، rows و تغییر schema نشان می‌دهد. |
| Audit export | `lineage` در evidence JSON همراه quality/schema drift export می‌شود. |

## مدل رویداد

هر `LineageEvent` شامل `sequence`، `operation`، `occurred_at`، `input_schema`، `output_schema`، `input_rows`، `output_rows` و `source` است. fingerprintهای قبل و بعد از schema تولید می‌شوند و سه summary مستقل ارائه می‌شود: `added_columns`، `removed_columns` و `dtype_changes`.

> رویداد lineage توضیح می‌دهد که **ساختار** و حجم داده چگونه تغییر کرده است، نه این‌که مقدار تک‌تک rowها چه بوده‌اند. برای حفظ privacy، eventها نباید PII، متن query شامل secret یا payload داده را نگه دارند.

## گردش کار پیشنهادی

پس از import، Trust Center را باز کنید و در صورت نیاز Quality Contract و Schema Baseline را تعریف نمایید. هر operation تحولی مانند rename/cast/drop/fill به‌صورت خودکار در lineage افزوده می‌شود. پیش از export یا handoff پروژه، **View lineage** را بازبینی کنید و evidence JSON را صادر نمایید. در پروژه‌های حساس، operationهایی که dtype یا nullability را تغییر داده‌اند باید همراه ticket تغییر و approval Data Steward بررسی شوند.

## نمونهٔ مفهومی

```text
#1 Imported dataset          rows — → 12,000     schema: source → 14 columns
#2 Renamed amount → revenue  rows 12,000 → 12,000 added: revenue; removed: amount
#3 Cast revenue to numeric   rows 12,000 → 12,000 types: revenue
#4 Dropped duplicate rows    rows 12,000 → 11,842 schema unchanged
```

## مرزهای فعلی و roadmap

این نسخه lineage را در سطح یک پروژهٔ desktop و DataFrame ثبت می‌کند. هنوز SQL parsing دقیق، column-to-column expression mapping، cross-project graph، dashboard/ML dependency، impact preview و server-side signed approval فعال نیستند. مرحلهٔ بعدی enterprise باید eventهای lineage را به Control Plane ارسال کند، dataset catalog و owner را اضافه نماید، و قبل از baseline/schema change یک impact analysis رو به downstream consumerها نمایش دهد.

## آزمون‌ها

آزمون `test_lineage_records_schema_only_transformations_and_project_persistence` rename و cast را ثبت می‌کند، absence مقدارهای email نمونه را در evidence تأیید می‌نماید، `.dsproj` را ذخیره/بازیابی می‌کند و ترتیب operationها را بررسی می‌نماید. suite هدفمند Trust Center و UI smoke پس از این تغییر شامل **۲۰ آزمون موفق** بود و اجرای کامل نهایی نیز **۸۰ آزمون موفق** با دو warning غیرمسدودکنندهٔ joblib را ثبت کرده است.

## منابع

[1]: https://www.snowflake.com/en/data-governance/data-lineage/tracking/ "Snowflake — Data Lineage Tracking: operational capture, change impact and governance"
[2]: https://aws.amazon.com/blogs/business-intelligence/enhance-data-governance-through-column-level-lineage-in-amazon-quicksight/ "AWS — Column-level lineage and schema-change impact analysis"
[3]: https://www.dataiku.com/blog/data-lineage "Dataiku — Lineage for root cause and impact analysis"
