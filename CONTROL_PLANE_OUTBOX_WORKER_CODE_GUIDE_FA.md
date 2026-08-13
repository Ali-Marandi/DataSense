# معماری Control Plane و صف Outbox/Worker برای مانیتورینگ Schema Drift

## وضعیت پیاده‌سازی و هدف این راهنما

Control Plane فعلی DataSense یک reference implementation برای SAML SP-initiated، PKCE، JWT، RBAC، tenant isolation و audit دارد. اجزای اجرایی آن شامل `bootstrap.py`، `main.py`، `rbac.py`، `saml.py`، `repositories.py` و PostgreSQL/Redis هستند. `PostgresEnterpriseRepository` هم‌اکنون connection pool و audit write را فراهم می‌کند؛ outbox/worker مانیتورینگ **هنوز به کد production Control Plane اضافه نشده است**.

این راهنما قرارداد و نمونه‌کد production-oriented برای افزودن آن قابلیت را ارائه می‌دهد. نمونه‌ها باید پیش از استقرار با migration، threat model، integration test، secret manager و notification provider واقعی تکمیل شوند. استفاده از outbox برای جلوگیری از dual-write میان database و notification/broker مناسب است: تغییر business state و outbox record در یک transaction commit می‌شوند و relay جداگانه delivery را انجام می‌دهد.[1] [2]

> Delivery در الگوی outbox معمولاً **at-least-once** است. worker یا مصرف‌کننده باید duplicate را با idempotency key بی‌اثر کند؛ «exactly once» صرفاً با یک `sent=true` ساده تضمین نمی‌شود.[1] [2]

## معماری هدف

```text
Desktop / Pipeline Agent
        │  POST SchemaObservation (metadata-only, authenticated)
        ▼
FastAPI Control Plane ── RBAC + tenant boundary + payload validation
        │
        ▼
PostgreSQL transaction
  schema_observations + schema_drift_incidents + audit_events + notification_outbox
        │ commit once
        ▼
Outbox Worker (polling + SKIP LOCKED, or CDC relay)
        │
        ├── Slack / Teams / Email / Pager
        ├── SIEM / ticketing
        └── durable broker (optional)

Metrics / DLQ / incident dashboard / runbook
```

Desktop فقط schema snapshot، fingerprint، row count و information طبقه‌بندی‌شده را می‌فرستد. مقدار cell، sample PII، token و secret منبع داده نباید در observation یا payload notification وجود داشته باشد. Control Plane مسئول policy version، severity، deduplication، routing و audit است.

## مدل دسترسی و مرز tenant

به permissionهای موجود `core/models.py` باید permissionهای زیر افزوده شوند. تمام endpointها organization را از `Principal` معتبر استخراج می‌کنند؛ `organization_id` در request body تنها برای consistency check استفاده می‌شود و نباید مبنای authorization باشد.

| Permission | نقش‌های معمول | کاربرد |
|---|---|---|
| `schema.observe` | agent/service principal، Data Steward | ثبت observation جدید. |
| `schema.read` | Owner، Admin، Data Steward، Auditor | مشاهدهٔ drift/incident. |
| `schema.policy.manage` | Owner، Admin، Data Steward | تعریف و approve policy versioned. |
| `schema.incident.ack` | Owner، Admin، Data Steward، on-call | acknowledge incident. |
| `schema.incident.resolve` | Owner، Admin، Data Steward | resolve با evidence/recheck. |
| `notification.manage` | Owner، Admin | تنظیم channel، escalation و retention. |

برای resource tenant دیگر، behavior مطلوب همان الگوی RBAC فعلی است: 404 عمومی و audit deny، نه disclosure وجود resource. SQL queryها باید `organization_id` را در predicate اجباری داشته باشند و production deployment باید Row-Level Security PostgreSQL را به‌عنوان defense-in-depth فعال کند.

## DDL پیشنهادی PostgreSQL

این DDL migration جدید است و جایگزین `schema.sql` فعلی نیست. نام channel یا destination حساس نباید payload قابل‌صادرات باشد؛ webhook secret فقط در secret manager نگه‌داری می‌شود و جدول صرفاً `secret_ref` دارد.

```sql
CREATE TYPE schema_incident_status AS ENUM ('open', 'acknowledged', 'resolved', 'suppressed');
CREATE TYPE outbox_status AS ENUM ('pending', 'processing', 'sent', 'dead');

CREATE TABLE datasets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  dataset_key TEXT NOT NULL,
  display_name TEXT NOT NULL,
  criticality TEXT NOT NULL CHECK (criticality IN ('tier_1', 'tier_2', 'tier_3')),
  owner_membership_id UUID REFERENCES memberships(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (organization_id, dataset_key)
);

CREATE TABLE schema_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  dataset_id UUID NOT NULL REFERENCES datasets(id),
  version INTEGER NOT NULL,
  policy_json JSONB NOT NULL,
  approved_by_membership_id UUID NOT NULL REFERENCES memberships(id),
  approved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  superseded_at TIMESTAMPTZ,
  UNIQUE (dataset_id, version)
);

CREATE TABLE schema_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  dataset_id UUID NOT NULL REFERENCES datasets(id),
  observed_at TIMESTAMPTZ NOT NULL,
  schema_fingerprint TEXT NOT NULL,
  schema_snapshot JSONB NOT NULL,
  row_count BIGINT,
  source_kind TEXT NOT NULL,
  correlation_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(schema_snapshot) = 'object')
);

CREATE TABLE schema_drift_incidents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  dataset_id UUID NOT NULL REFERENCES datasets(id),
  policy_version INTEGER NOT NULL,
  idempotency_key TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'high', 'critical')),
  status schema_incident_status NOT NULL DEFAULT 'open',
  decision TEXT NOT NULL CHECK (decision IN ('compatible', 'blocked')),
  diff_json JSONB NOT NULL,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  acknowledged_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  UNIQUE (organization_id, idempotency_key)
);

CREATE TABLE notification_outbox (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  incident_id UUID NOT NULL REFERENCES schema_drift_incidents(id),
  event_type TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  payload JSONB NOT NULL,
  status outbox_status NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  locked_at TIMESTAMPTZ,
  locked_by TEXT,
  last_error_code TEXT,
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX notification_outbox_ready_idx
  ON notification_outbox (available_at, created_at)
  WHERE status = 'pending';
CREATE INDEX schema_incidents_open_idx
  ON schema_drift_incidents (organization_id, dataset_id, last_seen_at DESC)
  WHERE status IN ('open', 'acknowledged');
```

## قرارداد observation و API FastAPI

Desktop باید `SchemaSnapshot.to_dict()` تولیدشده توسط محصول را ارسال کند و body size محدود شود. این request، row data ارسال نمی‌کند. `schema` با Pydantic validate می‌شود و policy evaluator به‌صورت server-side تصمیم می‌گیرد.

```python
# app/schema_monitor_api.py — نمونهٔ ساختار endpoint
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status

from .models import Permission, Principal
from .rbac import require_permission

router = APIRouter(prefix="/v1/datasets", tags=["schema-monitoring"])

class SchemaObservationIn(BaseModel):
    occurred_at: datetime
    schema_fingerprint: str = Field(min_length=32, max_length=128)
    schema_snapshot: dict
    row_count: int | None = Field(default=None, ge=0)
    source_kind: str = Field(pattern=r"^(desktop|pipeline|agent)$")

@router.post("/{dataset_id}/schema-observations", status_code=status.HTTP_202_ACCEPTED)
async def observe_schema(
    dataset_id: str,
    payload: SchemaObservationIn,
    principal: Principal = Depends(require_permission(Permission.SCHEMA_OBSERVE)),
    service = Depends(get_schema_monitor_service),
):
    incident = await service.observe(
        organization_id=principal.organization_id,
        actor_subject=principal.subject,
        dataset_id=dataset_id,
        observation=payload,
    )
    if incident is None:
        return {"decision": "compatible"}
    return {"decision": incident.decision, "incident_id": incident.id, "severity": incident.severity}
```

Endpoint باید request-id/correlation-id را بپذیرد یا تولید کند، rate limit داشته باشد، schema width/depth را محدود کند و payload log را redact نماید. service principalهای agent باید credential کوتاه‌عمر و rotateable داشته باشند؛ desktop client نباید webhook یا broker credential در خود نگه دارد.

## transaction اتمی: observation، incident، audit و outbox

عدم استفاده از outbox یعنی احتمال دارد incident در database ثبت شود ولی notification به‌دلیل network failure هرگز ارسال نشود، یا پیام ارسال شود ولی transaction database rollback شود. چهار write زیر باید در یک PostgreSQL transaction انجام شوند: observation، upsert incident، audit event و outbox row. pattern outbox دقیقاً برای حل همین dual write ساخته شده است.[1] [2]

```python
# app/schema_monitor_repository.py — نمونهٔ psycopg async
import json
from dataclasses import dataclass
from uuid import uuid4

@dataclass(frozen=True)
class OpenIncident:
    id: str
    severity: str
    decision: str

class SchemaMonitorRepository:
    def __init__(self, pool):
        self.pool = pool

    async def persist_decision_and_enqueue(
        self, *, organization_id: str, dataset_id: str, actor_subject: str,
        observed_at: str, fingerprint: str, snapshot: dict, row_count: int | None,
        policy_version: int, decision: str, severity: str, diff: dict,
        idempotency_key: str, correlation_id: str,
    ) -> OpenIncident | None:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO schema_observations
                          (organization_id, dataset_id, observed_at, schema_fingerprint,
                           schema_snapshot, row_count, source_kind, correlation_id)
                        VALUES (%s::uuid, %s::uuid, %s::timestamptz, %s, %s::jsonb,
                                %s, 'desktop', %s::uuid)
                        """,
                        (organization_id, dataset_id, observed_at, fingerprint,
                         json.dumps(snapshot), row_count, correlation_id),
                    )
                    if decision != "blocked":
                        await self._write_audit(cur, organization_id, actor_subject,
                                                "schema.observation.accepted", correlation_id)
                        return None

                    # One open incident per dataset + policy + observed fingerprint.
                    await cur.execute(
                        """
                        INSERT INTO schema_drift_incidents
                          (organization_id, dataset_id, policy_version, idempotency_key,
                           severity, decision, diff_json)
                        VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (organization_id, idempotency_key)
                        DO UPDATE SET last_seen_at = now()
                        RETURNING id::text, severity, decision, (xmax = 0) AS inserted
                        """,
                        (organization_id, dataset_id, policy_version, idempotency_key,
                         severity, decision, json.dumps(diff)),
                    )
                    incident_id, actual_severity, actual_decision, inserted = await cur.fetchone()
                    if inserted:
                        notification = {
                            "incident_id": incident_id,
                            "dataset_id": dataset_id,
                            "severity": actual_severity,
                            "decision": actual_decision,
                            "correlation_id": correlation_id,
                            "diff_summary": redact_diff(diff),
                        }
                        await cur.execute(
                            """
                            INSERT INTO notification_outbox
                              (organization_id, incident_id, event_type, idempotency_key, payload)
                            VALUES (%s::uuid, %s::uuid, 'schema_drift.blocked', %s, %s::jsonb)
                            """,
                            (organization_id, incident_id, f"notify:{idempotency_key}", json.dumps(notification)),
                        )
                    await self._write_audit(cur, organization_id, actor_subject,
                                            "schema.drift.blocked", correlation_id)
                    return OpenIncident(incident_id, actual_severity, actual_decision)
```

`redact_diff()` باید فقط field names، type changes، counts و policy reason را نگه دارد. raw column sample، PII value، SQL string حاوی secret و notification endpoint نباید وارد payload شوند. `ON CONFLICT` هم incident و هم outbox duplicate را کنترل می‌کند؛ incident تکراری فقط `last_seen_at` را به‌روزرسانی می‌کند.

## claim کردن امن batch توسط worker

چند worker هم‌زمان نباید یک outbox row را claim کنند. در PostgreSQL، `FOR UPDATE SKIP LOCKED` برای polling worker مناسب است. row در همان transaction به `processing` تبدیل می‌شود و lease کوتاه می‌گیرد. Worker بعد از process crash ممکن است event را دوباره ارسال کند؛ provider یا downstream باید idempotency key را دریافت کند.[1]

```python
# app/outbox_repository.py — claim batch با lease
CLAIM_SQL = """
WITH next_rows AS (
  SELECT id
  FROM notification_outbox
  WHERE status = 'pending' AND available_at <= now()
  ORDER BY created_at, id
  FOR UPDATE SKIP LOCKED
  LIMIT %s
)
UPDATE notification_outbox o
SET status = 'processing',
    locked_at = now(),
    locked_by = %s,
    attempts = attempts + 1
FROM next_rows
WHERE o.id = next_rows.id
RETURNING o.id::text, o.organization_id::text, o.incident_id::text,
          o.idempotency_key, o.event_type, o.payload, o.attempts;
"""

async def claim_batch(pool, worker_id: str, batch_size: int = 25):
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(CLAIM_SQL, (batch_size, worker_id))
                return await cur.fetchall()
```

lease recovery job باید rowهای `processing` قدیمی‌تر از timeout را به `pending` برگرداند. این job باید فقط پس از expiration lease اجرا شود و هر recovery event را log/audit کند؛ بدون lease timeout، crash worker می‌تواند row را برای همیشه stuck کند.

## worker: delivery، retry و dead-letter

Worker نباید transaction DB را هنگام فراخوانی Slack/Teams/Pager باز نگه دارد. ابتدا batch claim، سپس dispatch بیرون transaction، و در پایان `mark_sent` یا `schedule_retry` انجام می‌شود. `attempts`، retry time و error code باید ثبت شوند؛ body خطای provider ممکن است حاوی داده حساس باشد و نباید کامل persist شود.

```python
# app/outbox_worker.py — ساختار loop قابل‌تست
import asyncio
import random
from datetime import timedelta

MAX_ATTEMPTS = 8

async def run_once(repository, notifier, worker_id: str) -> int:
    rows = await repository.claim_batch(worker_id=worker_id, batch_size=25)
    for row in rows:
        try:
            await notifier.send(
                event_type=row.event_type,
                payload=row.payload,
                idempotency_key=row.idempotency_key,
            )
        except TransientNotificationError as exc:
            delay = min(900, 2 ** min(row.attempts, 8)) + random.uniform(0, 1)
            await repository.schedule_retry(
                row.id, available_in=timedelta(seconds=delay), error_code=exc.code,
                dead=row.attempts >= MAX_ATTEMPTS,
            )
        except PermanentNotificationError as exc:
            await repository.schedule_retry(row.id, available_in=None, error_code=exc.code, dead=True)
        else:
            await repository.mark_sent(row.id)
    return len(rows)

async def worker_loop(repository, notifier, worker_id: str):
    while True:
        delivered_or_queued = await run_once(repository, notifier, worker_id)
        await asyncio.sleep(0.2 if delivered_or_queued else 2.0)
```

`notifier.send()` باید HTTP timeout، TLS validation، allowlist destination، signed/integrity header و provider-specific idempotency header داشته باشد. `schedule_retry` باید status را به `pending` یا `dead` تغییر دهد. هنگام transition به `dead`، یک **monitor-the-monitor** alert از مسیر مستقل ایجاد شود؛ این alert نباید به همان notification channel خراب وابسته باشد.

## ابعاد schema drift و idempotency

idempotency key باید deterministic باشد و از organization، dataset، policy version، decision و fingerprint target ساخته شود. اگر همان drift دوباره مشاهده شود، incident جدید یا alert storm ایجاد نمی‌شود؛ `last_seen_at` به‌روز می‌شود. اگر fingerprint یا policy version تغییر کند، incident جدید یا update semantic مناسب ایجاد می‌شود.

```python
import hashlib

def incident_key(org_id: str, dataset_id: str, policy_version: int, fingerprint: str) -> str:
    material = f"{org_id}:{dataset_id}:{policy_version}:blocked:{fingerprint}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()
```

برای dataset Tier-1، policy routing می‌تواند `critical` را به Pager و SIEM، `high` را به Slack/Teams + ticket و `warning` را فقط به digest/dashboard هدایت کند. Criticality dataset باید از catalog مرکزی به‌دست آید، نه از payload agent.

## configuration و استقرار

| متغیر/تنظیم | نمونهٔ امن | نکته |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` از secret manager | application credential باید least privilege داشته باشد. |
| `REDIS_URL` | TLS/authenticated Redis | برای replay/short-lived state؛ outbox source of truth نیست. |
| `OUTBOX_POLL_INTERVAL_SECONDS` | `2` | متناسب با SLO و حجم؛ از busy loop پرهیز شود. |
| `OUTBOX_BATCH_SIZE` | `25` | با provider limit و latency تنظیم شود. |
| `OUTBOX_PROCESSING_TTL_SECONDS` | `300` | lease recovery باید کمتر از expiry واقعی نباشد. |
| `NOTIFICATION_SECRET_REF` | reference به KMS/Vault | webhook token داخل DB یا `.env` commit نمی‌شود. |
| `MAX_NOTIFICATION_ATTEMPTS` | `8` | پس از آن DLQ + owner alert. |

در dev، یک polling worker در compose قابل‌قبول است. برای production، worker process جدا، health/readiness endpoint، graceful shutdown، single responsibility، metrics و autoscaling لازم است. برای throughput بالاتر می‌توان PostgreSQL polling را با CDC مانند Debezium جایگزین کرد؛ CDC payload و retention را همچنان باید privacy/audit review کرد.[3]

## test و acceptance criteria

| test | نتیجهٔ لازم |
|---|---|
| transaction rollback | observation/incident/outbox هیچ‌کدام باقی نمانند. |
| database commit + worker restart | outbox pending بعد از restart delivery شود. |
| delivery success سپس crash پیش از mark-sent | duplicate ممکن باشد، اما provider/downstream با idempotency key side effect تکراری نداشته باشد. |
| دو worker هم‌زمان | هر row در یک لحظه فقط توسط یک worker claim شود. |
| repeated observation | outbox alert تکراری نسازد؛ فقط `last_seen_at` تغییر کند. |
| tenant mismatch | 404/deny + audit، بدون leakage. |
| endpoint failure | backoff، attempts، سپس `dead` و alert مستقل. |
| payload safety | email/PII sample/secret در outbox JSON و logs غایب باشند. |

## منابع

[1]: https://microservices.io/patterns/data/transactional-outbox.html "Microservices.io — Transactional outbox pattern"
[2]: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html "AWS Prescriptive Guidance — Transactional outbox pattern"
[3]: https://debezium.io/blog/2019/02/19/reliable-microservices-data-exchange-with-the-outbox-pattern/ "Debezium — Reliable microservices data exchange with the outbox pattern"
