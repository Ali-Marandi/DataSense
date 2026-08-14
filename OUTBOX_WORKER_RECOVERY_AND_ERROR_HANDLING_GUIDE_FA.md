# Recovery و مدیریت خطای Outbox/Worker در Control Plane

## وضعیت پیاده‌سازی

Control Plane فعلی DataSense یک reference implementation هویت/RBAC/Audit است. جدول `notification_outbox`، worker و endpoint مانیتورینگ مرکزی هنوز به service production افزوده نشده‌اند. بنابراین مثال‌های این سند **کد هدف production-oriented** هستند و قبل از استفاده باید همراه migration، test ترکیبی PostgreSQL/Redis، secret manager و fake notification sink در staging پیاده‌سازی شوند.

هدف recovery این است که eventهای commit‌شده گم نشوند، provider outage باعث block شدن API نشود، duplicate delivery اثر جانبی تکراری نسازد و eventهای غیرقابل‌تحویل به‌صورت قابل‌مشاهده quarantine شوند. transactional outbox رکورد event را همراه تغییر business state در یک transaction ذخیره می‌کند و relay جدا delivery را انجام می‌دهد؛ relay ممکن است پس از ارسال و پیش از ثبت موفقیت crash کند، بنابراین consumer/destination باید idempotent باشد.[1]

## state machine پیشنهادی

```text
pending ──claim──> processing ──delivery OK──> sent
   │                    │
   │                    ├── transient error ──> pending (available_at = backoff)
   │                    ├── permanent error ──> dead
   │                    └── worker lease expired ──> pending (recovered)
   │
   └── attempts exhausted ──> dead ──authorized redrive──> pending
```

| state | معنا | owner مجاز برای transition |
|---|---|---|
| `pending` | آمادهٔ claim بعد از `available_at` | worker، recovery job، authorized redrive. |
| `processing` | به یک worker با lease محدود واگذار شده | همان worker یا lease recovery job. |
| `sent` | delivery provider تأیید شده است | فقط worker؛ immutable جز retention/archival. |
| `dead` | retry متوقف؛ نیازمند triage و redrive کنترل‌شده | worker (exhausted/permanent) یا owner authorized. |

`processing` نباید بدون `locked_by` و `locked_at` معتبر وجود داشته باشد. `sent` صرفاً نشان‌دهندهٔ acknowledgment provider است؛ اگر provider idempotency را رعایت نکند، exactly-once business effect تضمین نمی‌شود.

## طبقه‌بندی خطا و سیاست retry

| دستهٔ خطا | نمونه | رفتار | علت |
|---|---|---|---|
| Transient | timeout، DNS موقت، TLS handshake موقت، HTTP 408/429/5xx | retry با exponential backoff + jitter | احتمال بهبود بدون تغییر payload. |
| Provider rate-limit | HTTP 429 + `Retry-After` | احترام به `Retry-After` یا backoff policy | جلوگیری از amplification outage. |
| Permanent | HTTP 400/404 برای payload/channel نامعتبر، schema validation نامعتبر | `dead` فوری یا پس از policy محدود | retry بدون تغییر موفق نمی‌شود. |
| Authentication/authorization provider | 401/403 از webhook/provider | `dead` یا circuit-open + alert امنیتی | secret/scope/config باید خارج worker اصلاح شود. |
| Payload safety violation | PII/secret detector یا payload size over limit | `dead` + security incident؛ redrive پس از redaction | notification نباید داده حساس حمل کند. |
| Database failure | serialization/connection loss | transaction rollback و retry operation محدود | state نیمه‌کاره persist نشود. |

برای `pending`، backoff پیشنهادشده `min(cap, base × 2^(attempts-1)) + jitter` است. مقدار base/cap باید environment-specific باشد و در config قرار گیرد. retry بدون cap، queue storm و provider outage را تشدید می‌کند. DLQ راهی برای ایزوله‌کردن messageهای پردازش‌نشده و بررسی علت failure است؛ max-receive/retry باید به‌اندازه‌ای تنظیم شود که retryهای مفید ممکن باشند، نه آن‌قدر کم که یک failure موقت message را quarantine کند.[2]

```python
# app/retry_policy.py
from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import timedelta

@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 8
    base_seconds: float = 2.0
    max_seconds: float = 900.0

    def delay(self, attempts: int, retry_after_seconds: float | None = None) -> timedelta:
        if retry_after_seconds is not None:
            return timedelta(seconds=min(max(retry_after_seconds, 0), self.max_seconds))
        exponent = max(attempts - 1, 0)
        bounded = min(self.max_seconds, self.base_seconds * (2 ** exponent))
        return timedelta(seconds=bounded + random.uniform(0, min(1.0, bounded * 0.1)))

    def exhausted(self, attempts: int) -> bool:
        return attempts >= self.max_attempts
```

در test، generator تصادفی jitter باید injectable یا seeded باشد تا assertion deterministic بماند.

## claim اتمی و lease کوتاه

چند worker نباید یک event را هم‌زمان process کنند. `FOR UPDATE SKIP LOCKED` lock rowهای در حال کار را skip می‌کند و امکان concurrency می‌دهد؛ query باید filter/order دارای index داشته باشد تا queue با رشد حجم افت نکند.[3]

```sql
WITH candidate AS (
  SELECT id
  FROM notification_outbox
  WHERE status = 'pending'
    AND available_at <= now()
  ORDER BY created_at, id
  FOR UPDATE SKIP LOCKED
  LIMIT $1
)
UPDATE notification_outbox AS o
SET status = 'processing',
    locked_by = $2,
    locked_at = now(),
    attempts = attempts + 1
FROM candidate
WHERE o.id = candidate.id
RETURNING o.id, o.idempotency_key, o.event_type, o.payload, o.attempts;
```

Worker transaction برای claim باید کوتاه باشد و پیش از network call commit شود. نگه‌داشتن DB transaction در طول HTTP request باعث lock pressure و queue convoy می‌شود. claim موفق فقط مالکیت کوتاه‌مدت را ثبت می‌کند؛ failure پس از commit با lease recovery درمان می‌شود.

## recovery از worker crash و lease expiry

پس از crash، row ممکن است در `processing` باقی بماند زیرا claim transaction قبلاً commit شده است. یک reaper مستقل و idempotent باید leaseهای منقضی را بازیابی کند. `locked_at` نباید تنها معیار باشد؛ status و expiry در `WHERE` مانع می‌شود که recovery rowی را که worker سالم آن را تازه کرده است، بدزدد.

```sql
-- app/outbox_recovery.sql
WITH stale AS (
  SELECT id
  FROM notification_outbox
  WHERE status = 'processing'
    AND locked_at < now() - make_interval(secs => $1)
  FOR UPDATE SKIP LOCKED
  LIMIT $2
)
UPDATE notification_outbox AS o
SET status = 'pending',
    available_at = now(),
    locked_at = NULL,
    locked_by = NULL,
    last_error_code = 'lease_expired'
FROM stale
WHERE o.id = stale.id
RETURNING o.id, o.organization_id, o.incident_id, o.attempts;
```

هر recovered event باید audit/metric داشته باشد. اگر یک event پیوسته lease-expire می‌شود، cause احتمالاً worker crash، payload poison، capacity starvation یا provider call بسیار طولانی است؛ بعد از threshold recovery باید `dead` یا human escalation انجام شود. recovery job نباید status `sent` یا `dead` را تغییر دهد.

```python
# app/recovery_service.py
async def recover_expired_leases(repository, policy, audit_sink) -> int:
    recovered = await repository.requeue_expired_leases(
        lease_seconds=policy.processing_lease_seconds,
        limit=policy.recovery_batch_size,
    )
    for event in recovered:
        await audit_sink.write_recovery(
            organization_id=event.organization_id,
            incident_id=event.incident_id,
            event_id=event.id,
            reason="lease_expired",
        )
    return len(recovered)
```

در production، audit writeهای recovery بهتر است با همان transaction requeue یا یک outbox audit داخلی اتمی شوند؛ network logging sync در reaper نباید recovery را متوقف کند.

## نهایی‌سازی delivery با optimistic ownership check

Worker نباید eventی را که lease آن را از دست داده یا worker دیگر recovery کرده است، به `sent` تبدیل کند. update نهایی باید id و `locked_by` را شرط کند. نتیجهٔ affected row برابر صفر یعنی owner باید از mutation بیشتر خودداری و anomaly را log کند.

```sql
UPDATE notification_outbox
SET status = 'sent',
    sent_at = now(),
    locked_at = NULL,
    locked_by = NULL,
    last_error_code = NULL
WHERE id = $1::uuid
  AND status = 'processing'
  AND locked_by = $2;
```

برای retry:

```sql
UPDATE notification_outbox
SET status = CASE WHEN attempts >= $3 THEN 'dead'::outbox_status ELSE 'pending'::outbox_status END,
    available_at = CASE WHEN attempts >= $3 THEN available_at ELSE now() + $4::interval END,
    locked_at = NULL,
    locked_by = NULL,
    last_error_code = $5
WHERE id = $1::uuid
  AND status = 'processing'
  AND locked_by = $2;
```

`$5` باید error code طبقه‌بندی‌شده و کوتاه باشد، نه body کامل HTTP/provider. Header Authorization، payload خام و secret نباید در `last_error_code`، audit event یا DLQ باشد.

## worker loop با error boundary

```python
# app/outbox_worker.py
from __future__ import annotations
import asyncio
from contextlib import suppress

async def process_event(event, repository, notifier, worker_id, retry_policy, audit):
    try:
        result = await notifier.send(
            event_type=event.event_type,
            payload=event.payload,
            idempotency_key=event.idempotency_key,
        )
    except ProviderRateLimit as exc:
        delay = retry_policy.delay(event.attempts, retry_after_seconds=exc.retry_after_seconds)
        await repository.release_for_retry(event.id, worker_id, delay, "provider_rate_limited", retry_policy.max_attempts)
    except TransientNotificationError as exc:
        delay = retry_policy.delay(event.attempts)
        await repository.release_for_retry(event.id, worker_id, delay, exc.safe_code, retry_policy.max_attempts)
    except PermanentNotificationError as exc:
        await repository.mark_dead(event.id, worker_id, exc.safe_code)
    except Exception:
        # Do not expose traceback/payload; capture structured correlation in protected logs.
        delay = retry_policy.delay(event.attempts)
        await repository.release_for_retry(event.id, worker_id, delay, "worker_unexpected_error", retry_policy.max_attempts)
        raise
    else:
        changed = await repository.mark_sent(event.id, worker_id, provider_message_id=result.message_id)
        if not changed:
            await audit.write_anomaly("outbox_lost_lease_before_ack", event.id)

async def worker_loop(repository, notifier, worker_id, retry_policy, shutdown_event):
    while not shutdown_event.is_set():
        events = await repository.claim_batch(worker_id, limit=25)
        if not events:
            await asyncio.sleep(2)
            continue
        for event in events:
            with suppress(Exception):
                await process_event(event, repository, notifier, worker_id, retry_policy, repository.audit)
```

در کد واقعی، هر failure باید transaction نهایی خود را داشته باشد، cancellation هنگام graceful shutdown باید claim جدید را متوقف کند و leaseهای گرفته‌شده بدون completion توسط reaper بازیابی شوند. `suppress` در مثال فقط برای ادامهٔ batch است؛ production باید exception count و structured error را metric/log کند.

## DLQ، triage و redrive کنترل‌شده

`dead` به‌معنای حذف event نیست. DLQ یک quarantine قابل‌ممیزی است که علت، correlation، attempts و زمان failure را نگه می‌دارد. messageهای DLQ برای debugging و redrive کنترل‌شده استفاده می‌شوند؛ retention باید طولانی‌تر از queue اصلی و متناسب با سیاست سازمان باشد.[2]

| گام | owner | کنترل لازم |
|---:|---|---|
| 1. Triage | on-call/Data Steward | error code، provider status، incident criticality، payload redaction. |
| 2. Diagnose | platform/security owner | channel secret، allowlist، contract/policy، provider health. |
| 3. Repair | owner مربوط | تغییر config یا code با change ticket. |
| 4. Redrive approval | authorized role | ticket، reason، scope، target environment، TTL. |
| 5. Redrive | service | status→pending، `redrive_count++`، new correlation/audit، نه reset بی‌ردپای attempts. |
| 6. Verify | owner + monitoring | idempotent sink receipt، sent/queue metrics، incident closure. |

```sql
-- redrive تنها از endpoint مجاز با actor/ticket ثبت‌شده اجرا شود
UPDATE notification_outbox
SET status = 'pending',
    available_at = now(),
    locked_at = NULL,
    locked_by = NULL,
    last_error_code = NULL,
    redrive_count = redrive_count + 1
WHERE id = $1::uuid
  AND status = 'dead';
```

Redrive bulk بدون filter، بدون rate limit و بدون بررسی provider health خطر alert storm دارد. برای incidentهای Tier-1، redrive باید batch کوچک، canary و stop-on-error داشته باشد.

## circuit breaker و backpressure

اگر یک notification destination به‌طور گسترده 5xx/timeout می‌دهد، worker نباید همهٔ eventها را بی‌وقفه retry کند. circuit breaker per destination/tenant پیشنهاد می‌شود: پس از threshold خطای transient، breaker `open` می‌شود؛ worker eventهای channel را با `available_at` عقب می‌اندازد؛ یک probe محدود برای `half-open` ارسال می‌شود؛ موفقیت breaker را می‌بندد. eventهای critical باید route جایگزین یا alert monitor-the-monitor داشته باشند، اما همان event نباید به صدها channel تکراری fan-out شود.

Backpressure metricها: pending depth، oldest pending age، processing lease expiry count، retry rate، dead rate، provider error rate و worker utilization هستند. thresholdها باید بر اساس SLO عملیاتی و capacity test تنظیم شوند، نه مقادیر ثابت حدسی.

## آزمون‌های recovery پذیرش

| شناسه | fault injection | assertion |
|---|---|---|
| R-01 | worker بعد از claim crash | event بعد از lease expiry requeue شود. |
| R-02 | provider بعد از delivery قبل از ack crash | duplicate delivery ممکن، sink side effect idempotent. |
| R-03 | HTTP 429 با Retry-After | `available_at` مطابق safe delay و attempts ثبت شود. |
| R-04 | 400 permanent | dead فوری/مطابق policy و audit security-safe. |
| R-05 | retry attempts exhausted | status dead، DLQ metric و escalation مستقل. |
| R-06 | دو reaper هم‌زمان | هر event حداکثر یک بار recover شود. |
| R-07 | worker lost lease سپس late success | mark_sent affected rows=0 و anomaly ثبت شود. |
| R-08 | redrive authorized/unauthorized | فقط permission مجاز transition انجام دهد؛ actor/ticket audit شود. |
| R-09 | provider outage گسترده | breaker/backpressure، queue integrity و no alert storm. |

## منابع

[1]: https://microservices.io/patterns/data/transactional-outbox.html "Microservices.io — Transactional outbox pattern"
[2]: https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html "AWS SQS — Using dead-letter queues"
[3]: https://www.netdata.cloud/academy/update-skip-locked/ "Netdata Academy — Using FOR UPDATE SKIP LOCKED for queue workflows"
