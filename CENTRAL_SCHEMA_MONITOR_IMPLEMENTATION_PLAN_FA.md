# مراحل پیاده‌سازی سرویس مرکزی مانیتورینگ و هشدار Schema Drift Guard

## هدف و اصل طراحی

هدف، تبدیل بررسی محلی Schema Drift Guard به یک سرویس چندسازمانی است که observationهای privacy-safe را از desktop agent یا pipeline دریافت کند، policy سازمان را به‌صورت مرکزی ارزیابی نماید، evidence ممیزی ایجاد کند و در صورت نیاز alert deduplicated به کانال مناسب ارسال نماید. این سرویس نباید row data، نمونهٔ PII یا secret منبع داده را دریافت یا نگهداری کند.

> اصل کلیدی: **Desktop تشخیص و تجربهٔ کاربر را فراهم می‌کند؛ Control Plane policy، routing، audit و عملیات هشدار را مالک می‌شود.**

## مرحلهٔ ۱ — تثبیت contractهای سرویس

ابتدا schemaهای نسخه‌دار برای observation، policy، incident و delivery تعریف می‌شوند. `SchemaObservation` باید تنها `organization_id`، `dataset_id`، `source_type`، `occurred_at`، snapshot/fingerprintهای schema و metadata حداقلی مانند row count را داشته باشد. `SchemaDriftDecision` علاوه بر diff، policy version، severity و reasonها را نگه می‌دارد. هر contract باید JSON Schema یا Pydantic model داشته باشد و integration test compatibility آن را enforce کند.

| Artifact | فیلدهای لازم | کنترل |
|---|---|---|
| Observation | org/dataset، source، timestamp، current fingerprint/schema | schema validation، tenant authorization، size limit و redaction. |
| Policy | compatibility flags، criticality، notification routing، version | RBAC، approval workflow و immutable version. |
| Incident | severity، status، owner، idempotency key، first/last seen | unique constraint برای incident باز. |
| Alert delivery | channel، outcome، attempts، correlation ID | outbox retry، backoff و dead-letter queue. |

## مرحلهٔ ۲ — PostgreSQL و audit/outbox

به `enterprise_control_plane` جدول‌های زیر افزوده شود: `datasets`، `schema_policies`، `schema_observations`، `schema_drift_incidents`، `notification_channels` و `notification_outbox`. تمام رکوردها `organization_id` داشته باشند و queryها tenant-scoped شوند. یک transaction باید decision، audit event و outbox record را هم‌زمان ذخیره کند؛ در نتیجه failure اتصال notification باعث گم‌شدن alert نمی‌شود.

| جدول | کلیدهای مهم | lifecycle |
|---|---|---|
| `datasets` | organization_id، dataset_key، owner_membership_id، criticality | catalog و ownership. |
| `schema_policies` | dataset_id، version، policy_json، approved_by | immutable پس از approval؛ policy جدید version تازه می‌گیرد. |
| `schema_observations` | dataset_id، fingerprint، observed_at | retention محدود و بدون value data. |
| `schema_drift_incidents` | idempotency_key، status، severity، first_seen/last_seen | unique برای incident باز و update برای event تکراری. |
| `notification_outbox` | incident_id، channel_id، status، attempts | delivery async و retry قابل‌ممیزی. |

## مرحلهٔ ۳ — APIهای authenticated و RBAC

endpointهای FastAPI باید پشت `require_permission` موجود قرار گیرند. agent با service principal کوتاه‌عمر یا token workload identity احراز هویت می‌شود؛ desktop کاربر عادی نباید secret notification را ببیند.

```text
POST /v1/datasets/{dataset_id}/schema-observations    permission: schema.observe
GET  /v1/datasets/{dataset_id}/schema-incidents       permission: schema.read
POST /v1/datasets/{dataset_id}/schema-policies        permission: schema.policy.manage
POST /v1/schema-incidents/{incident_id}/acknowledge   permission: schema.incident.ack
POST /v1/schema-incidents/{incident_id}/resolve       permission: schema.incident.resolve
POST /v1/notification-channels                         permission: notification.manage
```

هر endpoint باید organization را از principal بگیرد، نه از payload صرف. ID مربوط به organization دیگر باید 404 بازگرداند و audit denial تولید کند. payloadها باید با rate limit، maximum schema width و validation JSON محدود شوند.

## مرحلهٔ ۴ — policy evaluator و impact context

سرویس از منطق deterministic `compare_schema` استفاده می‌کند، اما policy مرکزی criticality و context business را اضافه می‌نماید. نتیجهٔ local ممکن است `blocked` باشد، اما severity مرکزی با توجه به Tier dataset، PII classification، شمار consumer و window release تعیین شود. در این مرحله lineage محلی DataSense می‌تواند operation آخر و schema fingerprintها را برای troubleshooting به observation پیوست کند؛ cell data ممنوع است.

Impact analysis اولیه باید owner و consumerهای catalog را برگرداند. پس از تکمیل Data Lineage Tracker، graph کنترل‌پلین می‌تواند drift column را با dashboard/model/exportهای متاثر پیوند دهد و recipient alert را دقیق‌تر انتخاب کند.

## مرحلهٔ ۵ — worker هشدار و channelها

worker مستقل outbox را poll یا از queue مصرف می‌کند. برای هر record، idempotency key را بررسی می‌کند، message redacted می‌سازد و به Slack/Teams/email/Pager/SIEM می‌فرستد. secretهای webhook یا SMTP فقط در secret manager وجود دارند. شکست delivery با exponential backoff retry می‌شود و پس از سقف attempts به dead-letter queue می‌رود؛ delivery failure نباید incident schema را resolve کند.

| channel | کاربرد | حداقل کنترل |
|---|---|---|
| Slack/Teams | owner و تیم data برای Warning/High | message thread dedupe، link incident و audit delivery. |
| Pager | High/Critical Tier-1 | escalation policy، ack timeout و on-call owner. |
| Email | digest و اطلاع مدیر | fallback؛ نه تنها مسیر برای incident High. |
| SIEM | correlation و compliance evidence | TLS، token rotation و event redaction. |
| Ticketing | remediation traceability | ticket id روی incident و auto-close فقط پس از compatible recheck. |

## مرحلهٔ ۶ — scheduler و triggerها

برای batch dataset، job پس از ingestion success یا در cron محدود اجرا می‌شود. برای stream/near-real-time، observation باید با event source یا worker پایدار ساخته شود؛ استفاده از sessionهای موقتی برای polling پرتکرار مناسب نیست. در استقرار managed، scheduler/worker باید سرویس product مستقر و پایدار باشد. فاصلهٔ check از criticality و freshness SLO مشتق می‌شود؛ هر ساعت برای dataset روزانه بدون readiness signal یک anti-pattern است.

## مرحلهٔ ۷ — observability خود سرویس

metrics ضروری شامل count observation/decision، incident open، alert delivery outcome، last successful check، queue depth، retry/dead-letter و MTTA/MTTR است. dashboard باید coverage Tier-1، incident age و alert failure را نشان دهد. alert monitor failure باید از alert schema drift جدا باشد تا سکوت سرویس با «نبود drift» اشتباه گرفته نشود.

## مرحلهٔ ۸ — security و privacy hardening

پیش از production، threat model، authorization test چندسازمانی، payload fuzzing، secret rotation، TLS، database encryption، audit retention، backup/restore، rate limiting و disaster recovery test اجباری است. approval policy تغییر baseline باید از producer جدا باشد و در محیط‌های حساس two-person approval، ticket/reference change و evidence امضاشده داشته باشد.

## مرحلهٔ ۹ — rollout مرحله‌ای

ابتدا یک tenant پایلوت و دو dataset Tier-2 انتخاب کنید؛ alert فقط dashboard/digest باشد. پس از اثبات detection/dedupe/routing، یک dataset Tier-1 را با Pager و runbook فعال کنید. سپس catalog، lineage impact و notification channelهای بیشتر را گسترش دهید. هر مرحله به exit criteria شامل test pass، delivery evidence، owner acknowledgement و rollback procedure نیاز دارد.

## آزمون‌های پذیرش production

| سناریو | نتیجهٔ مورد انتظار |
|---|---|
| dtype breaking change | incident High، یک alert deduplicated، audit record و owner routing. |
| تکرار observation با fingerprint یکسان | last_seen update بدون incident/alert جدید. |
| added column مجاز | compatible event در dashboard؛ بدون pager. |
| alert endpoint down | outbox retry، delivery failure metric و DLQ؛ incident باقی می‌ماند. |
| درخواست tenant دیگر | 404 و audit denial. |
| baseline update بدون permission | 403 و policy بدون تغییر. |
| payload شامل مقدار حساس | validation/redaction failure و عدم ذخیرهٔ raw value. |

## تعریف Done

سرویس زمانی «آمادهٔ production» تلقی می‌شود که observation contract، tenant RBAC، policy versioning، idempotent incident، outbox delivery، metrics/dashboard، runbook، backup/restore و integration test IdP/channelهای هدف واقعاً در environment staging اجرا و evidence آن‌ها ثبت شده باشد. داشتن تنها endpoint یا پیام Slack به‌تنهایی تعریف Done نیست.
