# معماری Kubernetes برای DataSense Control Plane و Outbox/Worker

## وضعیت و مرز استقرار

این بسته، معماری و manifestهای Kubernetes برای Control Plane، worker هدف outbox و observability را فراهم می‌کند. Control Plane موجود شامل FastAPI، PostgreSQL repository، Redis ephemeral state، SAML، PKCE، RBAC و audit foundation است. endpointهای `/health/live`، `/health/ready` و `/metrics` اکنون اضافه شده‌اند؛ readiness با query امن PostgreSQL بررسی می‌شود و metrics کم‌کاردینال HTTP صادر می‌شوند.

> **محدودیت مهم:** ماژول اجرایی `app.outbox_worker`، migration outbox و notification provider هنوز در سرویس production پیاده‌سازی نشده‌اند. manifest worker در `k8s/base/outbox-worker.yaml` یک template هدف است و نباید تا تکمیل migration، worker health endpoint، notifier و acceptance tests deploy شود.

این طراحی نیازمند Kubernetes، registry خصوصی، PostgreSQL/Redis managed یا سخت‌سازی‌شده، secret manager، Ingress/API gateway، Prometheus stack و مسئولیت عملیاتی مستمر است. default sandbox محل اجرای persistent Kubernetes یا production workload نیست؛ پیش از deployment باید cluster target، ownership و فرآیند secret/backup مشخص باشند.

## topology هدف

```text
Internet / Corporate Network
          │
    Ingress / API Gateway (TLS, WAF, rate limit)
          │
  ┌───────▼──────────────── Kubernetes namespace: datasense-control-plane ───────┐
  │   API Deployment (2+ pods, HPA, PDB)                                         │
  │     ├─ /health/live, /health/ready, /metrics                                 │
  │     ├─ SAML ACS / PKCE / RBAC / audit API                                    │
  │     └─ PostgreSQL transaction: observation + incident + audit + outbox       │
  │                                                                               │
  │   Outbox Worker Deployment (2+ pods, PDB)                                    │
  │     ├─ claim with FOR UPDATE SKIP LOCKED                                     │
  │     ├─ retry / lease recovery / DLQ                                          │
  │     └─ provider notification / SIEM / ticketing                              │
  └───────────────────┬─────────────────────────────────────────────────────────┘
                      │ TLS/private network only
        ┌─────────────┼─────────────────┬────────────────────┐
        ▼             ▼                 ▼                    ▼
 PostgreSQL       Redis            Enterprise IdP     Notification provider
 persistent data  replay/TTL       SAML metadata       Slack/Teams/email/Pager

Prometheus → ServiceMonitor → /metrics → Grafana / Alertmanager
```

API و worker دو Deployment مستقل‌اند، زیرا pattern بار، resource profile، failure domain و autoscaling آن‌ها متفاوت است. API باید latency/auth availability را حفظ کند؛ worker باید queue depth و oldest-event age را drain کند، بدون اینکه provider outage مسیر user request را block کند.

## موجودی manifestها

| فایل | کاربرد | وضعیت |
|---|---|---|
| `k8s/base/namespace.yaml` | namespace با Pod Security Admission سطح `restricted` | آمادهٔ استفاده بعد از بررسی policy cluster. |
| `k8s/base/serviceaccount.yaml` | ServiceAccount جدا و بدون auto-mounted API token | آماده؛ در صورت workload identity annotation overlay لازم است. |
| `k8s/base/control-plane.yaml` | API Deployment، Service، probes، resource request/limit و secret/config injection | آماده پس از جایگزینی image digest و secret. |
| `k8s/base/outbox-worker.yaml` | template worker، port metrics و graceful shutdown | **وابسته به worker code آینده**. |
| `k8s/base/network-policy.yaml` | default deny و نمونه egress/ingress allow | باید برای CNI، managed DB، IdP و provider واقعی overlay شود. |
| `k8s/base/pdb.yaml` | PDB برای API و worker | نیازمند replica count حداقل ۲. |
| `k8s/base/hpa.yaml` | HPA API بر مبنای CPU/memory | قابل استفاده؛ custom metric worker مرحلهٔ بعد است. |
| `k8s/base/servicemonitor.yaml` | scrape Operator-based Prometheus | فقط در cluster دارای Prometheus Operator CRD. |
| `k8s/base/kustomization.yaml` | resource composition | نقطهٔ ورود deploy. |

## API deployment و probes

`/health/live` فقط سالم‌بودن process را می‌سنجد. `livenessProbe` از این endpoint استفاده می‌کند تا Kubernetes فقط در process failure pod را restart کند. `/health/ready` callback repository را اجرا و `SELECT 1` روی PostgreSQL می‌زند؛ اگر dependency در دسترس نباشد، 503 می‌دهد. این رفتار pod را از Service endpoint خارج می‌کند، اما به‌علت outage database restart loop ایجاد نمی‌کند.

Kubernetes HPA بر اساس CPU، memory یا custom/external metric scale می‌کند؛ resource request باید تعریف شده باشد تا utilization-based HPA معنی داشته باشد.[1] HPA دارای scale-down stabilization در manifest است تا نوسان موقت ترافیک replica flapping نسازد.[1]

```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: http
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 3
```

این readiness جایگزین synthetic SAML flow یا write transaction test نیست. برای readiness بسیار عمیق، از queryهای پرهزینه، notification call و IdP request داخل probe خودداری کنید؛ آن‌ها می‌توانند outage dependency را تشدید کنند.

## worker deployment و lifecycle

Worker باید به‌صورت Deployment مستقل deploy شود و `SIGTERM` را بپذیرد. هنگام termination، worker ابتدا claim جدید را متوقف می‌کند، operationهای در حال اجرا را تا زمان grace period به پایان می‌رساند و سپس خارج می‌شود. eventهای lease گرفته‌شده ولی کامل‌نشده با reaper recovery به pending بازمی‌گردند. `preStop` فقط یک کمک برای graceful shutdown است؛ correctness نباید به sleep ثابت وابسته باشد.

```yaml
terminationGracePeriodSeconds: 45
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "kill -TERM 1; sleep 10"]
```

کارگرهای چندگانه باید claim اتمی `FOR UPDATE SKIP LOCKED` داشته باشند. recovery، idempotency، delivery retry و DLQ در [راهنمای recovery](OUTBOX_WORKER_RECOVERY_AND_ERROR_HANDLING_GUIDE_FA.md) تعریف شده‌اند. worker نباید تمام podهای API را در یک process مشترک اجرا کند؛ چنین طراحی‌ای deploy/restart و scaling را به هم گره می‌زند.

## secrets و config

هیچ secret در manifestهای base قرار نگرفته است. secret با نام `datasense-control-plane-secrets` باید توسط External Secrets Operator، CSI Secret Store یا فرآیند CI/CD امن ایجاد شود. credentialها شامل database URL، Redis URL، JWT keypair، SAML certificate/private key، audit HMAC key و notification secret reference هستند.

```yaml
# overlay example — valueها را هرگز در Git commit نکنید.
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: datasense-control-plane-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: organization-secret-store
    kind: ClusterSecretStore
  target:
    name: datasense-control-plane-secrets
  dataFrom:
    - extract:
        key: production/datasense/control-plane
```

یک ConfigMap فقط تنظیم‌های غیرحساس مانند interval worker، log level و environment flag را دارد. notification webhook/token یا SAML private key نباید در ConfigMap، Docker image، Kubernetes annotation، CLI argument یا Grafana label قرار بگیرد.

## security hardening

namespace به Pod Security Admission سطح restricted label شده است. Restricted policy اجرای non-root، عدم privilege escalation، seccomp runtime default و drop capabilityها را پشتیبانی می‌کند.[2] [3] manifestها `runAsNonRoot`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: [ALL]` و `seccompProfile: RuntimeDefault` را اعمال می‌کنند.

NetworkPolicy ابتدا همهٔ ingress/egress را deny می‌کند، سپس DNS، ingress، monitoring و database-service namespace را به‌صورت نمونه allow می‌کند. پیش از production، policy باید با CNI واقعی آزمایش شود. IdP و notification provider معمولاً خارج cluster هستند؛ egress آن‌ها باید با private endpoint، egress gateway یا CIDR/FQDN policy فراهم شود و به هیچ‌وجه با `0.0.0.0/0` بدون کنترل باز نگردد.

ServiceAccount پیش‌فرض را استفاده نکنید. اگر cloud workload identity لازم است، annotation آن فقط روی ServiceAccount و با least-privilege role اعمال می‌شود. RBAC Kubernetes برای workload صرفاً مجوزهایی مانند خواندن config/secret موردنیاز را می‌دهد؛ application RBAC برای کاربران DataSense موضوع جداگانه‌ای است.

## rollout و rollback

Build باید image immutable با digest تولید کند، SBOM و vulnerability scan داشته باشد و digest را به overlay promotion کند. ابتدا migration backward-compatible اعمال، سپس API canary، readiness/metrics و SAML staging check اجرا می‌شود. worker فقط بعد از آنکه outbox migration و fake-sink acceptance tests پاس شد با یک replica canary فعال می‌شود. HPA و افزایش replica بعد از مشاهده queue metrics انجام می‌شوند.

Rollback API باید امکان‌پذیر باشد، اما rollback schema فقط زمانی اجرا شود که migration reversible و eventهای queued سازگار باشند. برای outbox، delete کردن rowهای pending/dead به‌عنوان rollback ممنوع است. Event schema version در payload و migration plan باید قبل از deploy ثبت شود.

## دستورهای عملیاتی پایه

```bash
# Validate در CI با tools نصب‌شده در runner
kubectl kustomize enterprise_control_plane/k8s/base > /tmp/datasense-k8s.yaml
kubectl apply --server-side --dry-run=server -f /tmp/datasense-k8s.yaml

# Deploy واقعی فقط پس از جایگزینی digest و secret overlay
kubectl apply -k enterprise_control_plane/k8s/base
kubectl -n datasense-control-plane rollout status deploy/datasense-control-plane
kubectl -n datasense-control-plane get pods,svc,hpa,pdb
```

manifest base حاوی image placeholder `registry.example.invalid/...:REPLACE_WITH_DIGEST` است و intentionally deployable نیست تا هیچ‌کس accidentally image غیرقابل‌ردیابی را به production نفرستد.

## معیار Go/No-Go Kubernetes

| کنترل | Go | No-Go |
|---|---|---|
| Image | digest immutable، SBOM/scan مجاز | tag mutable یا critical vulnerability بدون exception. |
| Secrets | external injection و rotation test | secret در Git/log/manifest یا بدون owner. |
| API health | live/ready و restart test پاس | readiness false مثبت یا restart loop. |
| Network | least-privilege egress/ingress test پاس | default-allow یا dependency ضروری بدون route کنترل‌شده. |
| Database | migration/backup/restore و rollback evidence | migration غیرقابل‌بازگشت بدون recovery plan. |
| Worker | lease/retry/DLQ/fake-sink acceptance پاس | worker template بدون code/metrics به production برود. |
| Observability | metrics، dashboard، alert route و runbook موجود | alert بدون owner یا metric high-cardinality. |
| Load | baseline/steady/burst/soak/fault evidence | فقط unit test بدون capacity evidence. |

## منابع

[1]: https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/ "Kubernetes — Horizontal Pod Autoscaling"
[2]: https://kubernetes.io/docs/tasks/configure-pod-container/security-context/ "Kubernetes — Configure a Security Context for a Pod or Container"
[3]: https://kubernetes.io/docs/concepts/security/pod-security-standards/ "Kubernetes — Pod Security Standards"
