# CI/CD برای Control Plane و Kubernetes DataSense

## هدف و وضعیت

pipeline جدید دو مسیر مجزا دارد. مسیر نخست با هر push یا pull request روی `main` اجرا می‌شود و pytest کامل، render Kustomize، اعتبار JSON dashboard و client-side validation manifest را انجام می‌دهد. مسیر دوم فقط با اجرای دستی و approval محیط GitHub فعال می‌شود و manifest تاییدشده را با image digest immutable به کلاستر promote می‌کند.

> deploy خودکار به production بدون GitHub Environment approval، migration review، secret injection، baseline SLO و evidence پذیرش worker توصیه نمی‌شود. workflow فعلی API را promote می‌کند؛ worker عمداً با `replicas: 0` باقی می‌ماند تا migration outbox، fake-sink acceptance، alert routing و تصمیم امضاشدهٔ عملیات تکمیل شود.

## فایل‌های workflow

| فایل | trigger | مسئولیت | اثر مجاز |
|---|---|---|---|
| `.github/workflows/test.yml` | push/PR/main و dispatch | pytest کامل، render Kustomize، JSON dashboard و artifact rendered manifest | فقط read/upload artifact. |
| `.github/workflows/build.yml` | tag `v*` یا dispatch | بسته‌بندی و release Windows | انتشار assetهای desktop. |
| `.github/workflows/kubernetes-deploy.yml` | dispatch دستی + GitHub Environment | server-side dry-run، diff، apply و rollout API | اعمال manifest به کلاستر تاییدشده. |

برای CI normal branch، `contents: read` و concurrency با cancel-in-progress استفاده می‌شود تا run قدیمی PR منابع مصرف نکند. GitHub Actions به‌صورت پیش‌فرض workflowها را برای eventهای تعریف‌شده اجرا می‌کند و artifactها را می‌توان برای review manifest rendered نگه داشت.[1]

## پیش‌نیازهای یک‌باره

| مورد | تنظیم لازم | کنترل امنیتی |
|---|---|---|
| GitHub Environment | محیط‌های `staging` و `production` | production با required reviewer و منع self-approval. |
| Cluster credential | `KUBECONFIG_B64` در secret همان Environment | ServiceAccount مخصوص CI/CD، namespace-scoped و least privilege. |
| Container registry | image signed/immutable با `@sha256:` | tag mutable در workflow پذیرفته نمی‌شود. |
| Secrets runtime | External Secrets/CSI یا فرآیند secret manager | `datasense-control-plane-secrets` در Git قرار نگیرد. |
| Prometheus Operator | ServiceMonitor/PrometheusRule CRD | scrape/alert route در staging بررسی شود. |
| Migration role | job یا pipeline جدا با schema owner محدود | app/worker role هرگز DDL اجرا نکند. |

credential CI باید فقط به `datasense-control-plane` namespace و resourceهای ضروری `get/list/watch/apply/patch` دسترسی داشته باشد. در production از credential shared administrator یا kubeconfig کاربر شخصی استفاده نکنید. بهتر است identity کوتاه‌عمر cloud/OIDC جایگزین kubeconfig بلندمدت شود؛ workflow حاضر `KUBECONFIG_B64` را به‌عنوان سازگارترین حداقل شروع می‌پذیرد، نه design نهایی ایده‌آل.

## CI در pull request

پس از ایجاد PR، workflow `Verify DataSense` باید هر دو job را سبز کند. job test، `requirements.txt` و `enterprise_control_plane/requirements.txt` را نصب، سپس `python -m pytest -q` را با `QT_QPA_PLATFORM=offscreen` اجرا می‌کند. این متغیر crash headless Qt را که در sandbox قبلی مشاهده شد مهار می‌کند.

job Kubernetes با `kubectl kustomize` فایل base را render می‌کند. وجود placeholder digest به‌تنهایی failure نیست، زیرا base به‌صورت عمدی deployable نیست. dashboard JSON با `jq empty` کنترل می‌شود و manifest rendered با `kubectl apply --dry-run=client --validate=false` بررسی ساختاری می‌شود. validation CRDهای ServiceMonitor/PrometheusRule به cluster دارای Operator در مرحلهٔ promotion نیاز دارد؛ client-side dry-run جایگزین آن نیست.

Artifact `datasense-kubernetes-rendered-<SHA>` باید توسط reviewer platform بررسی شود. بررسی باید image placeholder، NetworkPolicy overlay، namespace label، resource limits، worker replicas و ServiceMonitor release label را پوشش دهد.

## promotion staging

workflow `Promote Control Plane to Kubernetes` را فقط از SHA تاییدشده اجرا کنید. input `image_ref` باید مانند `ghcr.io/owner/image@sha256:<digest>` باشد. استفاده از `latest`، tag version بدون digest یا image registry ناشناخته با failure متوقف می‌شود. Environment staging secret را inject می‌کند و workflow مراحل زیر را طی می‌نماید.

| مرحله | کنترل | شرط عبور |
|---|---|---|
| Render | جایگزینی digest با image تاییدشده | هیچ `REPLACE_WITH_DIGEST` باقی نماند. |
| Worker guard | `replicas: 0` | تا acceptance signed، worker اجرا نشود. |
| Server dry-run | admission/RBAC/schema validation | API server deploy را بپذیرد. |
| Diff | تغییرهای موردانتظار | exit code فقط ۰ یا ۱ باشد. |
| Apply | server-side apply با field manager مشخص | ownership field conflict نداشته باشد. |
| Rollout | `rollout status` و pod ready | readiness PostgreSQL واقعی سبز باشد. |
| Post-check | EndpointSlice/pod list | Service endpoint سالم باشد. |

Kubernetes readiness probe traffic را فقط به pod آماده هدایت می‌کند؛ HPA resource-based نیز به requestهای resource نیاز دارد.[2] [3] بنابراین درخواست/limit و `/health/ready` را حذف نکنید تا rollout ظاهراً سریع‌تر شود.

## promotion production

مراحل production همان staging است، اما approval جدا و ورودی‌ها باید از evidence staging بیایند. پیش از promotion این چهار evidence ضروری‌اند: migration backward-compatible با backup/restore test، SAML staging smoke، Prometheus target/alert route، و Load/soak/fault evidence. اگر هرکدام missing باشد، release باید No-Go بماند، نه اینکه با override workflow عبور کند.

مهاجرت database باید قبل از rollout API، با role جدا و خروجی ثبت‌شده اجرا شود. deploy workflow عمداً migration را اجرا نمی‌کند، زیرا schema change، rollout application و queue replay failure domainهای متفاوتی دارند. پس از migration، API canary و readiness بررسی می‌شود. worker تنها در change جدا و پس از تغییر overlay production از صفر به حداقل دو replica فعال می‌گردد.

## worker activation gate

برای فعال‌سازی worker، این مسیر اجرا می‌شود: schema outbox و quality observation اعمال شود؛ webhook fake sink با Idempotency-Key result تست شود؛ retry، lease expiry، dead-letter و redrive مورد پذیرش قرار گیرد؛ `datasense_outbox_*` metrics در Prometheus مشاهده شوند؛ Grafana panel و Alertmanager critical route در staging fire/resolve test بگذرانند؛ سپس PR مجزا replica worker را از صفر به دو تغییر دهد. این جداسازی مانع از فعال شدن accidental webhook delivery در deploy API می‌شود.

## rollback

برای مشکل API، rollback image digest از طریق dispatch با digest release قبلی انجام می‌شود؛ force-push یا تغییر tag ممنوع است. rollback schema فقط با migration plan reversible اجرا می‌شود. برای worker incident، ابتدا scale worker به صفر، eventهای processing را با lease expiry/recovery به pending برگردانید و provider status را بررسی کنید. eventهای dead/pending را delete یا false-sent نکنید. rollback باید ticket، owner، correlation/evidence و زمان تصمیم داشته باشد.

## گزینه‌های راه‌اندازی خودکار worker

| رویکرد | trade-off | هزینه | پیچیدگی setup |
|---|---|---|---|
| Worker در Kubernetes با deployment مستقل | نزدیک‌ترین معماری به outbox/Prometheus و مقیاس‌پذیری موردنیاز سازمانی | هزینهٔ کلاستر و عملیات | بالا؛ migration، secrets، runtime و on-call لازم است. |
| اجرای آزمایشی با fake sink در محیط staging | delivery logic و metrics را بدون مشتری واقعی تأیید می‌کند | پایین‌تر | متوسط؛ برای approval اولیه توصیه می‌شود. |
| اجرای زمان‌بندی‌شدهٔ موقت خارج از کلاستر | ساده برای batchهای کم‌حجم، اما latency/lease recovery ضعیف‌تر | بسته به host | پایین تا متوسط؛ برای production queue توصیه نمی‌شود. |

## منابع

[1]: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows "GitHub Actions — Events that trigger workflows"
[2]: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-probes "Kubernetes — Container probes"
[3]: https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/ "Kubernetes — Horizontal Pod Autoscaling"
