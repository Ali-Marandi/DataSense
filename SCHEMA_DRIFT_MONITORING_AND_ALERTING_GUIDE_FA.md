# پیکربندی مانیتورینگ و هشدار خودکار Schema Drift Guard

## وضعیت فعلی و هدف عملیات

Schema Drift Guard در نسخهٔ فعلی DataSense یک کنترل محلی و دستی در Trust Center است: کاربر baseline را تأیید می‌کند، بررسی drift را اجرا می‌کند و نتیجه را در evidence export می‌بیند. این رفتار برای بازبینی interactive مناسب است، اما **هنوز scheduler، alert delivery، queue، webhook یا incident workflow خودکار در محصول desktop فعال نیست**. بنابراین راهنمای حاضر معماری و پیکربندی production برای مرحلهٔ بعدی را مشخص می‌کند و نباید به‌معنای فعال‌بودن alert خودکار در v2.2.1 تلقی شود.

مانیتورینگ حرفه‌ای schema باید detection، classification، ownership، impact و response را ترکیب کند. منابع observability نیز بر تشخیص پیوستهٔ addition/removal/type change، routeکردن بر اساس severity/مالک، record approval و suppressکردن هشدارهای تکراری تأکید دارند.[1] [2]

## دو گزینهٔ استقرار

| رویکرد | شیوهٔ اجرا و مزیت | محدودیت | هزینه و پیچیدگی |
|---|---|---|---|
| **عامل زمان‌بندی‌شدهٔ سبک در محیط داده** | یک process کنترل‌شده در Windows Server یا runner داخلی، datasetهای تعریف‌شده را در زمان‌بندی مشخص باز می‌کند، Schema Drift Guard را اجرا و نتیجه را به endpoint مرکزی می‌فرستد. مناسب پایلوت، داده‌های on-premise و شروع سریع. | پایداری، secret rotation و observability وابسته به عملیات زیرساخت مشتری است؛ مدیریت policy در چند agent سخت‌تر می‌شود. | هزینهٔ زیرساخت اندک، ولی نیازمند یک runner پایدار و مدیریت محلی است. |
| **Control Plane مرکزی با job scheduler و alert outbox** | سرویس مرکزی، catalog dataset/policy/owner را نگه می‌دارد؛ runnerهای کنترل‌شده event می‌فرستند؛ outbox/queue alertها را با dedupe و retry به Slack/Teams/email/SIEM تحویل می‌دهد. مناسب enterprise و چندسازمانی. | نیازمند استقرار سرویس، database، secret manager، queue و اتصال notification است. | پیچیدگی اولیه بیشتر؛ مسیر پیشنهادی برای production جهانی و multi-tenant. |

برای DataSense سازمانی، گزینهٔ دوم توصیه می‌شود؛ زیرا تغییر schema یک کنترل مشترک میان producer، consumer و owner است و نیازمند policy، audit و routing مرکزی است. گزینهٔ نخست راه سبک‌تری برای پایلوت است و نباید به یک sandbox موقتی واگذار شود؛ process باید در محیطی پایدار و تحت مدیریت سازمان اجرا شود.

## معماری پیشنهادی Control Plane

```text
Dataset source / desktop agent / pipeline runner
        │  (authenticated schema observation)
        ▼
Schema Drift API ──► policy evaluator ──► audit_events + outbox
        │                    │                    │
        │                    ▼                    ▼
        │              PostgreSQL            queue worker
        │                    │                    │
        ▼                    ▼                    ▼
Trust Center UI       dashboard/metrics      Slack/Teams/Email/SIEM
```

Agent یا pipeline فقط schema metadata و fingerprint را ارسال می‌کند؛ row data، PII نمونه‌ای و credential منبع نباید در event قرار گیرد. Control Plane policy را ارزیابی، event ممیزی immutable تولید، idempotency/deduplication اعمال و سپس پیام را از outbox تحویل می‌دهد. Outbox اتمی مانع از این می‌شود که database update ثبت شود اما alert در اثر failure شبکه گم شود.

## Event contract پیشنهادی

هر بررسی باید یک event نسخه‌دار و بدون مقدار خام داده ایجاد کند. نمونهٔ زیر فقط قالب پیشنهادی است و endpoint محصولی فعال در v2.2.1 نیست.

```json
{
  "event_version": "1.0",
  "event_type": "schema_drift.detected",
  "occurred_at": "2026-08-13T12:00:00Z",
  "organization_id": "org_123",
  "dataset_id": "finance.revenue_daily",
  "contract_version": "3.2.0",
  "policy_name": "Revenue strict schema",
  "decision": "blocked",
  "baseline_fingerprint": "sha256:...",
  "current_fingerprint": "sha256:...",
  "diff": {
    "added_columns": ["region"],
    "removed_columns": [],
    "dtype_changes": ["amount"],
    "nullability_relaxations": ["amount"],
    "column_order_changed": false
  },
  "idempotency_key": "org_123:finance.revenue_daily:baseline:current:policy"
}
```

`idempotency_key` باید از organization، dataset، fingerprint baseline/current و policy version ساخته شود. تا زمانی که این tuple تغییر نکرده است، سیستم فقط یک incident باز داشته باشد و eventهای بعدی شمارنده/last-seen را update کنند. این سیاست از alert storm جلوگیری می‌کند.

## نگاشت severity و مسیر هشدار

| تصمیم/حالت | severity | پیش‌فرض مسیر ارسال | SLA پیشنهادی | اقدام خودکار |
|---|---|---|---|---|
| `not configured` روی dataset غیرحساس | Info | dashboard و digest روزانه برای Data Steward | ۵ روز کاری | ایجاد task برای approval baseline. |
| `compatible` بدون drift | None | فقط metric و audit | ندارد | هیچ پیام انسانی. |
| `compatible` با تغییر مجاز | Info | digest روزانه، owner در dashboard | ۲ روز کاری برای review | ثبت change log؛ عدم ایجاد incident. |
| `blocked` به‌علت افزودن ستون در policy سخت‌گیر | Warning | channel تیم داده و owner dataset | ۸ ساعت کاری | توقف export/pipeline فقط اگر policy آن را الزام کند. |
| `blocked` به‌علت حذف required column یا dtype change | High | pager/on-call data engineering، owner و ticket | ۱ ساعت | quarantine خروجی، توقف release وابسته و شروع runbook. |
| `blocked` به‌علت nullable relaxation در dataset حساس | High/Critical | on-call، Data Steward و Security/Compliance در صورت PII | ۳۰ تا ۶۰ دقیقه | جلوگیری از export حساس و حفظ evidence. |
| failure خود monitor یا stale check | Warning/High بر پایهٔ criticality dataset | platform on-call | ۴ ساعت یا کمتر | retry با backoff؛ پس از threshold incident مستقل. |

Severity نباید فقط از نوع diff تعیین شود. `dataset criticality`، وجود PII، تعداد consumerهای downstream، freshness SLO و وضعیت release نیز باید در policy مرکزی اثر داشته باشند. برای نمونه، حذف ستون از یک dataset آزمایشی ممکن است Warning باشد، اما همان اتفاق در گزارش مالی روزانه باید High/Critical تلقی شود.

## Metrics، dashboard و SLO

باید چهار دسته metric منتشر شود. تمام labelها محدود و دارای cardinality کنترل‌شده باشند؛ نام ستون یا dataset خام بدون catalog ID نباید label Prometheus باشد.

| Metric پیشنهادی | نوع | labelهای مجاز | کاربرد |
|---|---|---|---|
| `datasense_schema_drift_checks_total` | Counter | `organization_tier`, `decision`, `source_type` | حجم بررسی و نرخ block. |
| `datasense_schema_drift_events_total` | Counter | `severity`, `diff_type`, `policy_class` | نوع drift و روند risk. |
| `datasense_schema_drift_last_success_timestamp_seconds` | Gauge | `dataset_criticality`, `source_type` | تشخیص monitor stale. |
| `datasense_schema_drift_open_incidents` | Gauge | `severity`, `dataset_criticality` | queue/incident load. |
| `datasense_schema_drift_alert_delivery_total` | Counter | `channel`, `outcome` | موفقیت/خطای تحویل پیام. |
| `datasense_schema_drift_time_to_ack_seconds` | Histogram | `severity` | کیفیت پاسخ‌گویی تیم. |
| `datasense_schema_drift_time_to_resolution_seconds` | Histogram | `severity`, `resolution_type` | کارایی remediation. |

Dashboard عملیاتی باید در یک صفحه نشان دهد: تعداد checkها، block rate، driftهای باز براساس owner، age oldest incident، monitor freshness، delivery failure و top policyها. Dashboard مدیریتی باید trend ماهانه، درصد changeهای سازگار، MTTA/MTTR و تعداد جلوگیری‌شدن از release ناسازگار را ارائه کند. موفقیت عملیات با کاهش incidentهای ناشی از drift، کاهش MTTR و افزایش coverage datasetهای critical سنجیده می‌شود.[1]

SLO نمونه: «برای datasetهای Tier-1، حداقل ۹۹٪ checkهای برنامه‌ریزی‌شده در پنجرهٔ زمانی اجرا شوند؛ ۹۹٪ alertهای High در کمتر از پنج دقیقه از ایجاد event تحویل شوند؛ و ۹۰٪ incidentهای High در کمتر از چهار ساعت acknowledge شوند.» این اعداد باید با baseline واقعی سازمان کالیبره شوند، نه به‌صورت ادعای محصول عمومی.

## برنامهٔ زمان‌بندی checks

فاصلهٔ check باید به نوع داده وابسته باشد. datasetهای batch روزانه را پس از ingestion موفق بررسی کنید، نه در ساعت ثابت بدون اطلاع از readiness. برای stream یا event-driven pipeline، schema event را در شروع batch یا هنگام ثبت source schema ارزیابی کنید. برای Tier-1 با consumerهای نزدیک‌به‌بلادرنگ، trigger رویدادی یا runner دائمی مناسب‌تر از polling مکرر است. اجرای مکرر یک وظیفهٔ سنگین با sessionهای موقتی مناسب production نیست؛ job باید به‌صورت deterministic و پایدار در سرویس product اجرا شود.

| نوع dataset | trigger پیشنهادی | حداقل شرط |
|---|---|---|
| Batch روزانه | event پایان ingestion یا cron محدود | ingest success و metadata source در دسترس باشد. |
| Batch ساعتی | event pipeline یا check هر ساعت | dedupe با fingerprint و خاموش‌سازی alert تکراری. |
| Stream | webhook/source schema registration یا worker دائمی | backpressure، retry و circuit breaker. |
| Ad hoc desktop | manual check پیش از export | baseline و policy مشخص باشد. |

## پیکربندی notification channelها

هر channel باید در Control Plane به‌صورت یک integration سازمانی با RBAC و secret manager ذخیره شود. webhook URL، SMTP credential یا token bot نباید در `.dsproj`، log client یا alert payload قرار بگیرد. برای هر integration باید owner، channel مقصد، severity حداقل، retry policy و retention تعیین شود.

| Channel | مناسب برای | policy تحویل |
|---|---|---|
| Slack/Teams | همکاری و acknowledge سریع | message با link incident، dedupe thread و escalation اگر ack ثبت نشود. |
| Email | owner/manager و digest | برای High به‌تنهایی کافی نیست؛ delivery outcome log شود. |
| Pager/on-call | incidentهای High/Critical | فقط برای datasetهای Tier-1؛ escalation chain و quiet hours صریح. |
| SIEM | evidence و correlation امنیتی | event JSON redacted، immutable retention و correlation ID. |
| Ticketing | remediation قابل‌ردیابی | یک ticket برای هر idempotency key باز؛ auto-close فقط بعد از check سازگار. |

## Runbook برای رخداد `blocked`

1. Alert را acknowledge کنید، `incident_id`، dataset، policy version و fingerprintها را ثبت نمایید.
2. diff report را بررسی کنید و مشخص کنید تغییر addition/removal/dtype/nullability/order است؛ مقدارهای خام داده را در alert یا ticket کپی نکنید.
3. lineage و consumer catalog را بررسی کنید تا owner producer و consumerهای متاثر تعیین شوند.
4. اگر تغییر ناشی از migration تاییدشده است، contract version، migration plan و compatibility policy را از مسیر change approval به‌روزرسانی کنید؛ baseline را فقط پس از approval ایجاد کنید.
5. اگر تغییر ناخواسته است، pipeline/export حساس را طبق policy متوقف یا quarantine کنید، producer را به schema مورد انتظار بازگردانید و check را دوباره اجرا کنید.
6. پس از `compatible` شدن، incident را با علت، action، owner و evidence link ببندید. اگر تغییر باعث خروجی نادرست شد، post-incident review انجام دهید.

## Hardening ضروری پیش از production

پیاده‌سازی alert خودکار باید قبل از فعال‌سازی عمومی، authentication متقابل agent/API، tenant isolation در هر query، rate limit، idempotency، outbox retry، dead-letter queue، encryption in transit، secret rotation، redacted logging، retention policy و integration testهای delivery failure را داشته باشد. در مرحلهٔ بعد، approval برای تغییر baseline باید با role مستقل از producer، تاریخ انقضا برای approval و signed evidence bundle تقویت شود.

## منابع

[1]: https://www.acceldata.io/blog/tools-to-track-data-contracts-and-schema-changes-across-your-data-stack "Tracking data contracts and schema changes: detection, classification, ownership and enforcement"
[2]: https://www.metaplane.dev/platform/schema-change-alerts "Schema change alerts and historical audit trails"
[3]: https://docs.dynatrace.com/docs/observe/data-observability/alert-unexpected-schema-change "Unexpected schema-change monitoring workflow"
