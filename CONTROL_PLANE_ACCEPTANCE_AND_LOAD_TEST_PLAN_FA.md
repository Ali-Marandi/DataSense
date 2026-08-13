# برنامهٔ آزمون پذیرش و بارگذاری Control Plane و Outbox/Worker

## وضعیت و مرزبندی شواهد

Control Plane موجود DataSense شامل reference implementation برای SAML ACS، PKCE، JWT، RBAC، جداسازی tenant، Redis state و PostgreSQL repository است. outbox/worker مانیتورینگ و endpoint مشاهدهٔ Schema Drift هنوز به سرویس production افزوده نشده‌اند؛ بنابراین این سند **برنامه و معیار پذیرش پیش از استقرار** است، نه گزارش عبور عملکردی از یک environment مرکزی بالفعل.

مجموعهٔ فعلی repository، ۸۰ آزمون موفق دارد که ۴ مورد آن security-flow Control Plane را می‌سنجد. هیچ‌یک از این ۸۰ مورد جایگزین test ترکیبی PostgreSQL/Redis/IdP یا load test outbox نیست. آزمون‌های این سند باید پس از پیاده‌سازی migration، endpoint و worker اجرا و artifactهای آن‌ها کنار release candidate نگه‌داری شوند.

## اهداف آزمون

| هدف | اثبات موردنیاز | ضدالگو |
|---|---|---|
| درستی تصمیم policy | observation با policy سازگار/ناسازگار تصمیم صحیح تولید کند. | client decision را بدون server-side evaluation بپذیرد. |
| atomicity | observation، incident، audit و outbox با هم commit یا rollback شوند. | notification خارج transaction و بدون outbox ارسال شود. |
| isolation | organization دیگر به dataset/incident دسترسی یا existence hint ندهد. | تنها مخفی‌کردن button در UI. |
| delivery قابل‌بازیابی | crash/retry باعث از دست‌رفتن alert نشود. | علامت‌زدن sent پیش از پاسخ provider. |
| idempotency | observation تکراری alert storm نسازد. | ارسال notifier برای هر request تکراری. |
| مقیاس‌پذیری | workerهای موازی row یکسان را هم‌زمان process نکنند. | `SELECT` و `UPDATE` جدا و بدون lock. |
| observability | latency، error، queue depth، retry/DLQ و tenant-safe logs قابل‌مشاهده باشند. | اتکا به log متنی بدون metric/correlation. |

## محیط پذیرش الزامی

محیط test باید از production جدا باشد و دادهٔ واقعی مشتری، SAML assertion واقعی، certificate خصوصی، webhook secret یا PII نداشته باشد. هر run با deployment immutable، migration نسخه‌دار و reset قابل‌تکرار database آغاز می‌شود.

| جزء | پیکربندی test | کنترل |
|---|---|---|
| FastAPI Control Plane | حداقل دو replica در test بارگذاری | health/readiness و correlation ID. |
| PostgreSQL | نسخهٔ نزدیک production؛ database جدا | migration تازه و cleanup deterministic. |
| Redis | instance جدا با TLS/auth مانند production | TTL/replay/key-expiry test. |
| IdP | SAML sandbox یا fixture امضاشدهٔ test | certificate test فقط در محیط test. |
| Notification sink | fake HTTP server قابل fail/slow/retry | payload را validate و idempotency key را ثبت کند. |
| Load generator | Locust جدا از target | credential حداقلی test و clock همگام. |
| Metrics | Prometheus/OpenTelemetry یا معادل | snapshot پیش/حین/پس از run. |

## دادهٔ آزمون و personaها

چهار tenant test مجزا بسازید: `alpha` (Tier-1)، `beta` (Tier-2)، `gamma` (restricted) و `attacker` (بدون مجوز). هر tenant دست‌کم یک dataset، policy version، membershipهای Owner/Data Steward/Analyst/Viewer/Auditor و service principal agent دارد. اطلاعات شبیه‌سازی‌شده باید فقط metadata schema داشته باشد؛ برای نمونه ستون‌های `order_id`, `revenue`, `region`, `loaded_at` و fingerprintهای ساختگی.

| persona | رفتار آزمون | نتیجهٔ لازم |
|---|---|---|
| Pipeline agent | observation معتبر برای dataset خودش می‌فرستد. | 202 و decision سازگار/blocked صحیح. |
| Data Steward | policy را version می‌کند و incident را acknowledge/resolve می‌کند. | audit، RBAC و tenant filter رعایت می‌شوند. |
| Viewer | تلاش برای edit policy یا acknowledge. | 403/deny و audit؛ هیچ mutation. |
| Cross-tenant attacker | شناسهٔ dataset/incident tenant دیگر را ارسال می‌کند. | 404 یا deny امن؛ هیچ leak. |
| Worker | batch را claim، dispatch و state را نهایی می‌کند. | exactly-one claim هم‌زمان؛ at-least-once delivery idempotent. |
| Fault injector | notification timeout/5xx/slow response/crash ایجاد می‌کند. | backoff، lease recovery، DLQ و monitor alert. |

## ماتریس آزمون پذیرش

### API، RBAC و tenant boundary

| شناسه | setup و اقدام | assertion قابل‌ماشین | evidence |
|---|---|---|---|
| A-01 | agent مجاز observation compatible می‌فرستد. | 202، incident ایجاد نمی‌شود، audit `accepted` دارد. | response، DB snapshot، audit row. |
| A-02 | همان agent observation blocked می‌فرستد. | incident open، outbox pending و audit در یک transaction وجود دارند. | transaction-level DB assertions. |
| A-03 | body مخرب با organization_id متفاوت می‌فرستد. | organization از JWT principal گرفته شود؛ mismatch رد گردد. | 403/422 و audit deny. |
| A-04 | Viewer policy update یا incident resolve می‌زند. | 403، هیچ row mutation ندارد. | before/after checksum و audit. |
| A-05 | principal tenant beta شناسه alpha را می‌خواند. | 404/deny، response tenant alpha را فاش نکند. | HTTP response + access audit. |
| A-06 | access token expired/issuer/audience غلط است. | 401 قبل از repository query. | auth metric/audit redacted. |
| A-07 | payload بیش از size/depth مجاز است. | 413/422 و service بدون memory pressure باقی بماند. | response و runtime metric. |

### transaction و outbox

| شناسه | fault/action | assertion قابل‌ماشین | evidence |
|---|---|---|---|
| O-01 | پیش از commit exception تزریق کنید. | observation/incident/audit/outbox همگی rollback شوند. | چهار count برابر صفر. |
| O-02 | blocked observation commit شود. | incident و outbox با correlation_id واحد دیده شوند. | query join + audit export. |
| O-03 | همان observation/fingerprint دوباره ارسال شود. | outbox جدید ایجاد نشود؛ `last_seen_at` update شود. | unique idempotency assertion. |
| O-04 | دو worker هم‌زمان claim کنند. | هر row توسط حداکثر یک `locked_by` claim شود. | worker trace + DB state. |
| O-05 | worker پس از provider success و پیش از `mark_sent` crash کند. | re-delivery ممکن، ولی sink با idempotency key side effect تکراری ندارد. | sink receipt count و idempotency record. |
| O-06 | provider timeout/5xx بدهد. | attempts++، `available_at` future با backoff و status pending. | outbox row + metric. |
| O-07 | attempts به حد برسد. | status `dead` و incident ثانویه/monitor alert ایجاد شود. | DLQ row + alert evidence. |
| O-08 | worker lease expire شود. | stale `processing` به pending برگردد و فقط یک بار recover audit شود. | lease recovery query/event. |

### SAML/PKCE و operationهای ترکیبی

جریان SAML باید در load test جدا از production IdP و با IdP sandbox اجرا شود. assertion replay، امضای نامعتبر، audience/destination غلط، expiry و RelayState/PKCE mismatch باید negative test باشند. هدف این testها اثبات behavior امنیتی است، نه تولید بار سنگین علیه IdP سازمان.

| شناسه | اقدام | نتیجهٔ لازم |
|---|---|---|
| S-01 | AuthnRequest + ACS assertion معتبر test | code یک‌بارمصرف و token scope صحیح. |
| S-02 | همان assertion ID دوباره | replay reject، audit deny، code جدید صادر نشود. |
| S-03 | code exchange دوبار | فقط نخستین PKCE exchange موفق. |
| S-04 | role membership حین session تغییر | policy refresh/TTL مطابق SLA مصوب و audit change. |

## SLOهای پیشنهادی و قواعد Go/No-Go

اعداد زیر **هدف آغازین برای محیط staging** هستند و ادعای performance فعلی نیستند. پیش از production باید با hardware، concurrency، payload size، database plan و notification provider واقعی baseline شده و توسط owner SRE/security تصویب شوند.

| indicator | بار baseline پیشنهادی | معیار Go | معیار No-Go |
|---|---|---|---|
| Observe API p95 | steady-state با حجم تعیین‌شده تیم | زیر budget مصوب و error rate زیر budget | عبور پایدار از budget یا saturation. |
| blocked decision تا outbox commit | همان request | atomic commit و trace کامل | incident/outbox/audit ناقص یا orphan. |
| worker latency | queue دارای mix severity | queue age و retry مطابق SLO مصوب | depth یا oldest age دائماً رو به رشد. |
| duplicate delivery | fault O-05 | sink side effect دقیقاً یک‌بار | provider action تکراری بدون dedupe. |
| cross-tenant test | هر load stage | صفر leak و صفر mutation مجاز | هر leak/unauthorized write. |
| DLQ rate | injection محدود 5xx | alert در زمان policy، recovery قابل‌اثبات | silent dead job. |
| database lock wait | peak worker concurrency | بدون convoy/deadlock غیرقابل‌قبول | lock timeout/deadlock یا p95 رشد شدید. |

Go/No-Go باید با evidence کامل تصمیم‌گیری شود: گزارش Locust CSV/HTML، snapshot metric، query plan dequeue، log correlation، DB invariants، receiptهای fake sink، security test report و rollback drill. یک average latency مناسب به‌تنهایی مجوز production نیست؛ p95/p99، error budget، data integrity و queue age باید با هم بررسی شوند.

## پروفایل‌های بارگذاری

هر stage باید از warm-up عبور کند، به steady-state برسد و زمان cooldown برای drain queue داشته باشد. دادهٔ واقعی یا notification provider واقعی در load test استفاده نشود.

| stage | هدف | الگوی اجرا | مشاهدهٔ اصلی |
|---|---|---|---|
| Smoke | wiring و credential test | 1–5 virtual user، چند دقیقه | 0 error، dashboard/trace. |
| Baseline | latency بدون saturation | ramp تدریجی تا concurrency ابتدایی | p50/p95، DB query plan. |
| Steady | ظرفیت عملیاتی | concurrency مصوب برای 30–60 دقیقه | RPS، error، queue age، CPU/memory. |
| Burst | spike ingestion | ramp سریع سپس drain | backpressure، oldest pending، recovery time. |
| Soak | leak و backlog | بار متوسط برای چند ساعت | memory، connection pool، retry/DLQ drift. |
| Fault | reliability | timeout/5xx/crash worker/Redis restart | rollback، idempotency، recovery. |
| Scale | worker concurrency | worker 1→N با batch size متغیر | throughput vs lock wait/queue depth. |

آزمون را با یک `rate` خیالی شروع نکنید. نرخ observation واقعی یا forecast شدهٔ مشتری، criticality dataset، payload width و budget SLO را به‌عنوان ورودی ثبت کنید. اگر دادهٔ workload واقعی موجود نیست، baseline staging را برای مقایسهٔ relative profileها تولید کنید و از آن برای تعهد ظرفیت production استفاده نکنید.

## Locust: نمونهٔ test client

Locust رفتار HTTP را با Python تعریف و throughput، response time و error را مشاهده/خروجی می‌دهد.[1] سناریوها باید با tokenهای test محدود اجرا شوند و bodyها metadata-only باشند. فایل زیر وقتی endpoint `/v1/datasets/{dataset_id}/schema-observations` پیاده‌سازی شد، نقطهٔ شروع است.

```python
# enterprise_control_plane/loadtests/locustfile.py
import os
from uuid import uuid4
from locust import HttpUser, task, between

DATASET_ID = os.environ["LOADTEST_DATASET_ID"]
ACCESS_TOKEN = os.environ["LOADTEST_ACCESS_TOKEN"]

class SchemaAgentUser(HttpUser):
    wait_time = between(0.2, 1.0)

    def on_start(self):
        self.headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Correlation-ID": str(uuid4()),
        }

    @task(8)
    def compatible_observation(self):
        payload = {
            "occurred_at": "2026-08-14T12:00:00Z",
            "schema_fingerprint": "a" * 64,
            "schema_snapshot": {
                "columns": [
                    {"name": "order_id", "dtype": "string", "nullable": False},
                    {"name": "revenue", "dtype": "float64", "nullable": False},
                ]
            },
            "row_count": 1000,
            "source_kind": "pipeline",
        }
        with self.client.post(
            f"/v1/datasets/{DATASET_ID}/schema-observations",
            json=payload,
            headers=self.headers,
            name="POST /schema-observations [compatible]",
            catch_response=True,
        ) as response:
            if response.status_code != 202 or response.json().get("decision") != "compatible":
                response.failure(f"unexpected response: {response.status_code}")

    @task(2)
    def blocked_observation(self):
        payload = {
            "occurred_at": "2026-08-14T12:00:01Z",
            "schema_fingerprint": "b" * 64,
            "schema_snapshot": {
                "columns": [{"name": "order_id", "dtype": "integer", "nullable": True}]
            },
            "row_count": 1000,
            "source_kind": "pipeline",
        }
        with self.client.post(
            f"/v1/datasets/{DATASET_ID}/schema-observations",
            json=payload,
            headers=self.headers,
            name="POST /schema-observations [blocked]",
            catch_response=True,
        ) as response:
            if response.status_code != 202 or response.json().get("decision") != "blocked":
                response.failure(f"unexpected response: {response.status_code}")
```

نمونهٔ commandهای staging:

```bash
# در یک host تولیدکنندهٔ بار جدا از target اجرا شود
locust -f enterprise_control_plane/loadtests/locustfile.py \
  --host=https://control-plane.staging.example \
  --headless -u 50 -r 5 -t 20m \
  --html=artifacts/locust-steady.html \
  --csv=artifacts/locust-steady
```

Locust userها Python class هستند و taskهای weightدار به‌صورت random انتخاب می‌شوند؛ در نتیجه نسبت compatible/blocked در مثال 8:2 است.[2] `catch_response=True` برای validate کردن semantic response و علامت‌زدن پاسخ نادرست به‌عنوان failure استفاده می‌شود.[2]

## آزمون load worker و queue

Load HTTP به‌تنهایی کافی نیست. برای worker، ابتدا حجم مشخصی outbox row از طریق API یا seed fixture ایجاد کنید، سپس N worker را اجرا کنید. در هر run ثبت کنید: queue depth اولیه/نهایی، oldest pending age، rows claimed، `sent`, `dead`, retry count، duplicate receipt و lock wait.

`FOR UPDATE SKIP LOCKED` به workerهای هم‌زمان اجازه می‌دهد rowهای lock‌شده را skip و row بعدی را claim کنند؛ index ترکیبی بر predicate dequeue و ordering برای سلامت queue مهم است.[3] query plan باید در staging با `EXPLAIN (ANALYZE, BUFFERS)` بررسی شود و با رشد حجم queue دوباره اندازه‌گیری شود.

```sql
-- invariant بعد از drain: هیچ pending قدیمی‌تر از SLO مجاز نیست
SELECT count(*) AS stale_pending
FROM notification_outbox
WHERE status = 'pending'
  AND available_at < now() - interval '5 minutes';

-- invariant idempotency: هر کلید notification فقط یک row دارد
SELECT idempotency_key, count(*)
FROM notification_outbox
GROUP BY idempotency_key
HAVING count(*) > 1;

-- visibility: وضعیت queue
SELECT status, count(*), min(created_at) AS oldest
FROM notification_outbox
GROUP BY status;
```

## ترتیب اجرای release candidate

ابتدا migration را روی database خالی اعمال کنید و pytest/integration test را اجرا نمایید. سپس acceptance API/transaction و security negative tests را اجرا کنید. بعد smoke Locust، baseline، steady، burst، soak و fault injection را به‌ترتیب اجرا نمایید. تنها پس از آن scale test worker، backup/restore و rollback drill اجرا می‌شود. هر stage اگر invariant امنیتی یا data integrity را نقض کرد، stage بعدی شروع نمی‌شود.

## منابع

[1]: https://docs.locust.io/en/stable/what-is-locust.html "Locust — What is Locust?"
[2]: https://docs.locust.io/en/stable/writing-a-locustfile.html "Locust — Writing a locustfile"
[3]: https://www.netdata.cloud/academy/update-skip-locked/ "Netdata Academy — Using FOR UPDATE SKIP LOCKED for queue workflows"
