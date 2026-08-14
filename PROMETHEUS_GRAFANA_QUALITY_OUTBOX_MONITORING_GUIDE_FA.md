# مانیتورینگ Prometheus، داشبورد Grafana و هشدارهای Quality Gate/Outbox

## وضعیت پیاده‌سازی

Control Plane اکنون endpoint `/metrics` و متریک‌های HTTP کم‌کاردینال را در `enterprise_control_plane/app/metrics.py` صادر می‌کند. `ServiceMonitor` و dashboard/PrometheusRule نیز در `enterprise_control_plane/k8s/monitoring/` اضافه شده‌اند.

> متریک‌های `datasense_quality_gate_*` و `datasense_outbox_*` تعریف شده‌اند، اما تا زمانی که endpoint مرکزی Quality Gate، migration outbox و worker واقعی پیاده‌سازی نشوند، مقدار عملیاتی تولید نمی‌کنند. پنل‌های Grafana مربوط به آن‌ها ممکن است **No data** نشان دهند؛ این رفتار درست و شفاف است، نه نشانهٔ عبور یا خطای سیستم.

## اصول label و حریم خصوصی

Prometheus time-series را با ترکیب نام metric و label ذخیره می‌کند. labelهای پرکاردینال، هزینه و latency query را افزایش می‌دهند و می‌توانند PII/شناسه‌های سازمانی را افشا کنند. بنابراین نام کاربر، email، organization ID، dataset ID، request/correlation ID، assertion ID، URL دارای UUID، raw error text و payload نباید label باشند.

| مجاز | ممنوع |
|---|---|
| `method`, `route`, `status` | raw URL مانند `/datasets/uuid` |
| `outcome`, `event_type` کنترل‌شده | message body یا provider error text |
| `decision`, `policy_tier` محدود | contract name یا tenant slug |
| `service`, `severity` | email/subject/role list |

middleware API route template را بعد از route resolution می‌گیرد، نه URL خام را؛ بنابراین `/v1/datasets/{dataset_id}` به‌عنوان یک series واحد ثبت می‌شود.

## فهرست metricها

| Metric | نوع | وضعیت | کاربرد |
|---|---|---|---|
| `datasense_control_plane_http_requests_total` | Counter | فعال | request count بر پایه method/route/status. |
| `datasense_control_plane_http_request_duration_seconds` | Histogram | فعال | p50/p95/p99 latency API. |
| `datasense_control_plane_authorization_decisions_total` | Counter | hook آینده | outcome مجوز، بدون tenant/resource. |
| `datasense_control_plane_saml_validations_total` | Counter | hook آینده | outcome SAML بدون assertion. |
| `datasense_quality_gate_decisions_total` | Counter | hook آینده | approved/blocked/not-configured. |
| `datasense_outbox_delivery_attempts_total` | Counter | hook آینده | delivery outcome. |
| `datasense_outbox_pending_events` | Gauge | hook آینده | backlog جاری queue. |
| `datasense_outbox_oldest_pending_age_seconds` | Gauge | hook آینده | oldest pending age. |
| `datasense_outbox_processing_leases` | Gauge | hook آینده | leaseهای processing. |
| `datasense_outbox_dead_events` | Gauge | hook آینده | DLQ/dead count. |
| `datasense_outbox_lease_recoveries_total` | Counter | hook آینده | stale lease requeue count. |

## اتصال Prometheus Operator

`ServiceMonitor` به Prometheus Operator نیاز دارد. label `release: kube-prometheus-stack` باید با selector واقعی Prometheus installation شما هماهنگ شود. اگر Prometheus Operator ندارید، همان endpoint `/metrics` را با static scrape config یا Pod annotations scrape کنید؛ هر دو روش را هم‌زمان بدون دلیل عملیاتی استفاده نکنید.

```yaml
# Verify after deploy
kubectl -n datasense-control-plane get servicemonitor
kubectl -n datasense-control-plane get svc datasense-control-plane
# In Prometheus UI: Status > Targets, confirm /metrics target is UP.
```

در کلاسترهای دارای NetworkPolicy، namespace monitoring باید اجازهٔ TCP به port 8080 API و port 9090 worker را داشته باشد. scrape failure می‌تواند ناشی از Service selector، endpoint، RBAC Operator، TLS/mTLS یا NetworkPolicy باشد؛ آن را با restart application پنهان نکنید.

## اتصال Quality Gate به metric

وقتی endpoint مرکزی contract execution ساخته شد، پس از تصمیم نهایی—نه قبل از validation—counter را افزایش دهید. `policy_tier` باید enum محدود مانند `sandbox`, `standard`, `tier_1`, `restricted` باشد؛ نام policy یا tenant label نشود.

```python
from .metrics import QUALITY_GATE_DECISIONS

async def emit_gate_decision(report, policy, policy_tier: str):
    decision = report.gate_decision(policy)
    QUALITY_GATE_DECISIONS.labels(
        decision=decision.decision,
        policy_tier=policy_tier,
    ).inc()
    return decision
```

اگر فقط desktop local اجرا می‌شود، این metric در Control Plane افزایش نمی‌یابد. ارسال metric از desktop به مرکزی باید metadata-only، authenticated و rate-limited باشد؛ Prometheus push از هر desktop client به shared gateway بدون طراحی tenancy توصیه نمی‌شود.

## اتصال worker به metric

worker پس از هر delivery attempt، recovery یا queue refresh metric را به‌روزرسانی می‌کند. query gaugeها باید aggregate باشد و row detail/tenant را metric label نکند.

```python
from .metrics import (
    OUTBOX_DEAD, OUTBOX_DELIVERIES, OUTBOX_OLDEST_PENDING_SECONDS,
    OUTBOX_PENDING, OUTBOX_PROCESSING_LEASES, OUTBOX_LEASE_RECOVERIES,
)

async def refresh_outbox_gauges(repository) -> None:
    stats = await repository.outbox_stats()  # aggregate-only SQL: no payloads/tenant ids
    OUTBOX_PENDING.set(stats.pending)
    OUTBOX_PROCESSING_LEASES.set(stats.processing)
    OUTBOX_DEAD.set(stats.dead)
    OUTBOX_OLDEST_PENDING_SECONDS.set(stats.oldest_pending_age_seconds)

async def record_delivery(event_type: str, outcome: str) -> None:
    OUTBOX_DELIVERIES.labels(event_type=event_type, outcome=outcome).inc()

async def record_lease_recovery() -> None:
    OUTBOX_LEASE_RECOVERIES.inc()
```

`event_type` نیز باید finite allowlist باشد، مانند `schema_drift.blocked` و `quality_gate.blocked`؛ user-provided string به label تبدیل نشود.

## PromQLهای اصلی

| هدف | PromQL | تفسیر |
|---|---|---|
| API RPS | `sum(rate(datasense_control_plane_http_requests_total[5m]))` | نرخ درخواست کل. |
| API 5xx ratio | `sum(rate(...{status=~"5.."}[5m])) / clamp_min(sum(rate(...[5m])), 1)` | نسبت error server. |
| p95 latency | `histogram_quantile(0.95, sum by (le) (rate(datasense_control_plane_http_request_duration_seconds_bucket[5m])))` | latency tail، نه average. |
| Gate blocked rate | `sum(rate(datasense_quality_gate_decisions_total{decision="blocked"}[15m]))` | surge policy/data issue. |
| Pending backlog | `max(datasense_outbox_pending_events)` | اگر پیوسته بالا رود، worker عقب افتاده است. |
| Oldest age | `max(datasense_outbox_oldest_pending_age_seconds)` | زمان انتظار قدیمی‌ترین event. |
| DLQ | `max(datasense_outbox_dead_events)` | event نیازمند triage؛ صفر هدف است. |
| Lease churn | `sum(increase(datasense_outbox_lease_recoveries_total[15m]))` | crash/timeout/lease sizing issue. |

## داشبورد Grafana

فایل `enterprise_control_plane/k8s/monitoring/grafana-dashboard.json` را از Grafana UI import یا با provisioning repository وارد کنید. Datasource variable باید به UID واقعی Prometheus تغییر کند. dashboard شامل هفت پنل است: request rate، p95 latency، 5xx ratio، Gate decision rate، pending/dead events، oldest pending age و delivery/recovery outcomes.

Dashboard باید سه time range داشته باشد: ۱ ساعت برای incident response، ۶ ساعت برای rolling degradation و ۷ روز برای capacity/trend. datasource یا namespace variable را تغییر دهید، اما tenant variable ایجاد نکنید. drill-down از dashboard باید به runbook، trace و audit event با correlation ID حفاظت‌شده برود، نه به payload outbox یا PII.

## Alerting و routing

فایل `prometheus-rules.yaml` alertهای availability، 5xx، p95 latency، Gate blocking surge، backlog، oldest age، DLQ و repeated lease recovery دارد. thresholdها **staging defaults** هستند و باید پس از load/soak/fault baseline توسط owner SRE/security کالیبره شوند. Grafana alert rule شامل query، condition، evaluation interval/duration، label، annotation و notification routing است.[1]

| Alert | severity پیشنهادی | اولین پاسخ |
|---|---|---|
| API unavailable | critical | Service endpoints، readiness، NetworkPolicy، deployment rollout. |
| 5xx/latency | warning | dependency health، trace، DB pool، HPA saturation. |
| Gate blocked surge | warning | upstream contract/policy/schema drift review؛ داده را silent تغییر ندهید. |
| Queue backlog | warning | worker count، provider breaker، lock wait، queue age. |
| Oldest event late | critical | incident owner، provider route، worker health و retry state. |
| DLQ event | critical | triage error code، payload safety، approved redrive. |
| Lease recovery loop | warning | worker crash، timeout، lease TTL، capacity. |

Alertmanager/Grafana contact point باید routeهای جدا برای `severity=critical` و `severity=warning` داشته باشد. critical باید به on-call و ticket/SIEM، warning به engineering channel و digest هدایت شود. alert باید owner، runbook URL، service و severity داشته باشد؛ credential، payload و PII در annotation ممنوع است. Alert ruleها threshold و duration دارند، بنابراین یک spike کوتاه نباید بدون `for` مناسب paging ایجاد کند.[1]

## Recording rules و performance

Queryهای گران یا پرتکرار را recording rule کنید. recording ruleها result query را به time series جدید تبدیل می‌کنند و query dashboard/alert را کم‌هزینه‌تر می‌سازند.[1] در `prometheus-rules.yaml`، 5xx ratio و oldest pending age نمونه‌های recording rule هستند. recording rule به‌معنای داشتن SLO نیست؛ SLO باید owner، window، error budget و remediation policy داشته باشد.

## runbook incident outbox

در alert oldest-age یا backlog، ابتدا status worker pod و ServiceMonitor target را بررسی کنید. سپس pending/processing/dead gauge، provider error outcome، retry rate و lease recovery را بررسی نمایید. در PostgreSQL، query aggregate queue health و lock wait را اجرا کنید، نه payloadها را. اگر provider outage است، circuit breaker و alternate route policy را بررسی کنید؛ backlog را با delete یا forced sent پاک نکنید. DLQ فقط با ticket، authorization و redrive audit دوباره pending شود.

## runbook Gate block surge

ابتدا scope و زمان شروع blocking rate را ببینید. تغییر contract/policy، freshness regression، schema drift یا upstream pipeline deployment را بررسی کنید. report evidence را export کنید و failure را به data defect، rule config error یا execution error تفکیک نمایید. auto-blocking باید action حساس را hold کند؛ disable کردن Gate یا تغییر baseline بدون approval، remediation نیست.

## معیار پذیرش observability

| سناریو | assertion |
|---|---|
| API request | `/metrics` HTTP counter و histogram را بدون raw route افزایش دهد. |
| postgres unavailable | `/health/ready` 503 شود و pod از Service endpoint خارج شود؛ liveness همچنان process-only باشد. |
| Gate blocked | decision counter فقط با enum محدود افزایش یابد. |
| worker retry | delivery counter outcome و backlog/age gauge به‌روز شود. |
| stale lease | lease recovery counter افزایش و trace/audit redacted ثبت شود. |
| DLQ | dead gauge و critical route alert فعال شود. |
| provider outage | queue metrics/alerts دیدپذیر باشند؛ API request block نشود. |
| dashboard import | همهٔ active metricها داده داشته باشند؛ future worker panelها تا deploy شدن No data را شفاف نمایش دهند. |

## منابع

[1]: https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rules/ "Grafana — Alert rules"
[2]: https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/ "Kubernetes — Horizontal Pod Autoscaling"
