# راهنمای اتصال Customer Activation به Transactional Outbox و گذار Fail-Closed به Production

## پاسخ اجرایی

Triggerهای activation باید به‌صورت **event-driven و rule-based** روی Transactional Outbox فعلی سوار شوند، نه به‌عنوان cron هوشمند یا webhook مستقیم از desktop. Control Plane هم‌اکنون الگوی ضروری را دارد: enqueue اتمی و tenant-scoped، کلید idempotency، claim با `FOR UPDATE SKIP LOCKED`، lease recovery، retry با jitter، DLQ و metricهای کم‌کاردینال.[1] قابلیت activation باید همین primitiveها را توسعه دهد، اما دو کنترل افزوده لازم دارد: **ارزیابی policy پیش از enqueue** و **ارزیابی مجدد policy در لحظهٔ delivery**. در نبود هر شرط compliance، اثر خارجی نباید رخ دهد.

> قاعدهٔ fail-closed: اگر consent، tenant policy، recipient verification، channel allow-list، payload schema یا version policy قابل‌اثبات نیست، trigger نباید به channel خارجی تحویل شود. به‌جای retry نامحدود یا ارسال احتمالی، suppression audit می‌شود و فقط cue محلی یا task انسانیِ مجاز باقی می‌ماند.

## ۱. چرا Outbox موجود پایهٔ مناسبی است

| قابلیت موجود | کاربرد برای activation | مرز موردنیاز |
|---|---|---|
| transaction tenant-scoped و RLS | state activation، audit و enqueue در یک commit | policy decision و suppression هم باید همان‌جا ثبت شود. |
| `(organization_id, idempotency_key)` unique | جلوگیری از ایجاد چندبارهٔ یک trigger | effect delivery نیز به execution table یکتا نیاز دارد. |
| `SKIP LOCKED` و lease | مقیاس‌دادن worker بدون claim هم‌زمان | worker باید پیش از external effect policy را دوباره بخواند. |
| retry + jitter + max attempts | مدیریت خطای موقت channel | policy denial نباید به retry یا DLQ عادی تبدیل شود. |
| DLQ و lease recovery | visibility خطاهای عملیاتی | `suppressed` باید از `dead` متمایز باشد. |
| metric بدون payload logging | observability privacy-safe | labelها نباید org، account، email، URL یا reason متن‌آزاد باشند. |

## ۲. جریان پیشنهادی end-to-end

```text
Desktop / Control Plane domain event
  → validate event schema + metadata allow-list
  → resolve tenant activation policy + consent
  → [DENY] atomic audit + activation_suppression; no external outbox event
  → [ALLOW] atomic activation-state update + audit + outbox enqueue
  → Outbox worker claim (lease/skip-locked)
  → re-evaluate current policy + recipient/channel verification
  → [DENY/REVOKED] record final suppression; no external effect
  → [ALLOW] idempotent trigger execution + template render + delivery
  → sent | retry | dead
```

### مرحلهٔ A — رخداد دامنه و ingest

Desktop یا Control Plane تنها eventهای allow-listed زیر را می‌سازد: `dataset_imported`، `contract_created`، `checks_run`، `audit_exported`، `signed_bundle_verified` و timeoutهای computed از state. هر event فقط شناسه‌های pseudonymous، timestamp، event code، outcome و counter bounded دارد. نام dataset، schema fingerprint، نام ستون، مقدار rule، cell value، email، path فایل، error text، token و URL خارجی در payload ممنوع‌اند.[2]

API ingest باید authorization tenant-scoped و schema validation را **قبل از هر write** اجرا کند. event نامعتبر با error code ثابت رد و در metric شمرده می‌شود؛ raw payload در log ثبت نمی‌شود.

### مرحلهٔ B — policy gate پیش از enqueue

`ActivationPolicyService.evaluate()` باید دست‌کم این ورودی‌ها را بررسی کند: `organization_id`، feature flag tenant، consent version، data/metadata classification، channel policy، activation-case status، quiet period و trigger version. خروجی آن یک enum پایدار است، نه متن آزاد:

| outcome | رفتار |
|---|---|
| `allow_in_app` | cue یا task داخلی مجاز است؛ Outbox event نوع `activation.in_app.v1` ساخته می‌شود. |
| `allow_external` | تنها پس از recipient mapping verified، Outbox event نوع `activation.external.v1` ساخته می‌شود. |
| `suppress_no_consent` | suppression و audit اتمی؛ هیچ external event ساخته نمی‌شود. |
| `suppress_policy_denied` | suppression و audit اتمی؛ هیچ external event ساخته نمی‌شود. |
| `suppress_quiet_period` | suppression و next-eligible timestamp؛ هیچ delivery فوری ساخته نمی‌شود. |
| `reject_invalid_payload` | API error ثابت و audit security outcome؛ بدون queue. |

عملیات state، audit و enqueue باید مانند `record_quality_gate_observation` در یک transaction انجام شود. نمونهٔ کلید idempotency: `activation:{case_id}:{trigger_code}:{policy_version}`. اگر insertion به علت conflict رد شد، پاسخ API باید idempotent success برگرداند، نه اینکه event تازه بسازد.[3]

### مرحلهٔ C — policy gate دوم در worker

Consent و policy ممکن است بعد از enqueue تغییر کنند. از این رو، `ActivationDeliveryClient` باید پیش از resolve کردن recipient یا call کردن provider، policy را دوباره ارزیابی کند. این نقطه نباید صرفاً به payload قدیمی اعتماد کند.

| وضعیت در لحظهٔ delivery | رفتار final | دلیل |
|---|---|---|
| consent revoked، tenant paused، policy deny یا recipient unverified | `suppressed` | اثر خارجی نامجاز است؛ retry آن را مجاز نمی‌کند. |
| template/channel version removed | `suppressed` + security/config alert | fail-closed نسبت به configuration drift. |
| provider timeout یا 5xx | `retry` | خطای موقت است و با retry bounded بازیابی می‌شود. |
| provider 4xx permanent بعد از validation | `dead` | خطای فنی/پیکربندی است و نیازمند triage دارد. |
| in-app cue/task write success | `sent` | اثر مجاز و idempotent تکمیل شده است. |
| external delivery success | `sent` | فقط پس از ثبت execution idempotent. |

**اصلاح schema ضروری:** وضعیت `suppressed` باید final و جدا از `dead` باشد. `dead` به failure غیرمنتظره یا misconfiguration فنی اختصاص دارد؛ policy denial یک نتیجهٔ compliance درست است و نباید alert خطای delivery یا DLQ را آلوده کند.

### مرحلهٔ D — اثر idempotent و destination privacy-safe

قبل از delivery، worker باید در جدول `activation_trigger_executions` یک row با unique key `(organization_id, activation_case_id, trigger_code, trigger_version)` ایجاد کند. تنها writer موفق اثر را انجام می‌دهد. اگر event دوباره تحویل شد، handler اثر را skip کرده و نتیجهٔ idempotent را گزارش می‌کند.

recipient نباید در payload Outbox باشد. handler آن را در لحظهٔ delivery از profile امن tenant resolve می‌کند و فقط وقتی channel، recipient verification و consent همگی Green هستند، template ID و parameterهای non-sensitive را به provider می‌دهد. متن آزاد error provider نیز در event/log نگهداری نمی‌شود؛ فقط error code allow-listed ثبت می‌شود.

## ۳. تغییرات code و schema

| جزء | تغییر لازم | کنترل fail-closed |
|---|---|---|
| `activation.py` جدید | policy evaluation، transition state و trigger selection | default outcome = suppress؛ فقط allow-list مسیر external می‌سازد. |
| `repositories.py` | transaction واحد برای activation case، audit، suppression و Outbox | `set_config('app.organization_id')` پیش از query؛ idempotency conflict بی‌اثر. |
| `schema.sql` | `activation_cases`، `activation_trigger_executions`، `activation_suppressions`؛ افزودن `suppressed` به outbox status | RLS در تمام جدول‌های tenant؛ unique index برای execution. |
| `outbox.py` | `DeliveryResult` outcome تازهٔ `suppressed` و `mark_suppressed()` | policy result final؛ no retry، no external effect. |
| `activation_delivery.py` جدید | policy re-check، secure destination resolver، template-ID delivery | هیچ recipient/payload حساس در Outbox یا metric نیست. |
| `outbox_worker.py` | route event typeهای versioned به adapter activation | worker health، kill switch و graceful shutdown. |
| `metrics.py` | metricهای activation و policy، با label bounded | منع labelهای tenant/account/email/URL/raw error. |
| `trust_center_tab.py` | نمایش in-app cue، دلیل reason code و Pause automation | کاربر/tenant admin کنترل قابل‌فهم دارد. |

### Interface پیشنهادی

```python
@dataclass(frozen=True)
class ActivationDecision:
    outcome: Literal[
        "allow_in_app", "allow_external", "suppress_no_consent",
        "suppress_policy_denied", "suppress_quiet_period", "reject_invalid_payload"
    ]
    policy_version: str
    reason_code: str

async def evaluate_and_enqueue_trigger(..., event: ActivationSourceEvent) -> ActivationDecision:
    # validate → tenant policy/consent → atomic state/audit/suppression/outbox
    ...
```

`DeliveryResult` باید outcome `suppressed` را اضافه کند؛ worker در آن حالت `mark_suppressed(event_id, reason_code)` را اجرا می‌کند و counter `activation_trigger_outcomes_total{outcome="suppressed"}` را افزایش می‌دهد. این تغییر از retry ناخواستهٔ یک delivery نامجاز جلوگیری می‌کند.

## ۴. metricهای لازم برای rollout

### اصل label و retention

همهٔ metricها باید بدون `organization_id`، `account_id`، `email`، `dataset_id`، `request_id`، raw URL یا exception text باشند. reason، event_type و channel فقط از enum محدود استفاده کنند. telemetry activation باید فقط بعد از approval consent/policy فعال شود.[4]

### Metricهای compliance و policy

| metric پیشنهادی | نوع | labelهای مجاز | هدف rollout Green |
|---|---|---|---|
| `datasense_activation_policy_decisions_total` | Counter | `outcome`, `trigger_code`, `policy_version` | ۱۰۰٪ decisionها enum معتبر؛ هیچ `unknown` در ۷ روز. |
| `datasense_activation_suppressions_total` | Counter | `reason_code`, `trigger_code` | suppression قابل‌توضیح؛ افزایش ناگهانی alert شود. |
| `datasense_activation_external_delivery_blocked_total` | Counter | `reason_code`, `channel` | صفر bypass؛ eventهای block شده audit trail دارند. |
| `datasense_activation_payload_rejections_total` | Counter | `reason_code`, `event_type` | صفر payload rejected در production cohort پس از hardening. |
| `datasense_activation_consent_revocations_total` | Counter | `source` | ۱۰۰٪ revocationها حداکثر طی ۵ دقیقه به gate delivery اعمال شوند. |
| `datasense_activation_kill_switch_state` | Gauge | `scope` (`global`,`tenant`) | وضعیت قابل‌مشاهده و tested در drill. |

### Metricهای operational Outbox

| metric | تعریف / آستانهٔ پیشنهادی Green | Red |
|---|---|---|
| oldest pending age | p95 کمتر از ۵ دقیقه در ۷ روز، پس از نمونهٔ حداقل ۵۰۰ event | بیشتر از ۱۵ دقیقه برای ۱۵ دقیقه متوالی یا no worker owner. |
| dead-event rate | کمتر از ۰٫۱٪ از deliveryهای eligible در ۷ روز | بیشتر از ۱٪ یا هر dead event با severity امنیتی. |
| retry exhaustion | کمتر از ۰٫۵٪ eventهای eligible | بیش از ۲٪ یا روند افزایشی دو روزه. |
| duplicate-effect rate | صفر؛ با replay/chaos test اثبات شود | هر اثر دوباره‌شده. |
| stale-lease recovery | baseline ثبت و trend پایدار؛ recovery نباید اثر duplicate بسازد | surge غیرعادی یا lease recovery بدون processing. |
| worker health / metrics scrape | ۱۰۰٪ workerهای cohort healthy و scrapeable | هر worker بدون health/metrics یا trigger queue بدون owner. |

آستانه‌های عددی policy پیشنهادی برای cohort اولیه‌اند؛ پیش از قراردادن در SLA، باید با حجم و channel واقعی pilot بازنگری شوند.

### Metricهای activation و ارزش محصول

| metric | Green rollout criterion | Yellow | Red |
|---|---|---|---|
| Time to First Trusted Report | median کمتر از ۳۰ دقیقه و p90 کمتر از ۶۰ دقیقه | median ۳۰–۶۰ دقیقه | median بیش از ۶۰ دقیقه یا data-loss complaint |
| evidence completion | بیش از ۸۰٪ deliverableهای qualified | ۵۰–۸۰٪ | کمتر از ۵۰٪ |
| Contract reuse هفتهٔ چهارم | بیش از ۵۰٪ runهای معتبر | ۲۵–۵۰٪ | کمتر از ۲۵٪ |
| reviewer handoff روز ۱۴ | بیش از ۶۰٪ accountهای qualified | ۳۰–۶۰٪ | کمتر از ۳۰٪ |
| in-app trigger completion | baseline cohort + بهبود معنادار نسبت به no-trigger control | اثر نامعلوم | افزایش trigger volume بدون completion |
| unwanted-trigger / opt-out | کمتر از ۱٪ accountهای eligible | ۱–۳٪ | بیش از ۳٪ یا شکایت privacy/security |

این metricها تنها وقتی معتبرند که cohort qualification، تعریف event و consent یکسان باشد. افزایش شمار trigger یا event به‌تنهایی activation یا retention محسوب نمی‌شود.

## ۵. گیت‌های Red / Yellow / Green و production rollout

### مرحله‌بندی rollout

| مرحله | cohort | قابلیت فعال | شرط خروج |
|---|---|---|---|
| ۰. internal | کارکنان / test tenant | in-app only، synthetic و test events | testهای privacy، RLS، idempotency و rollback پاس شوند. |
| ۱. design partner | حداکثر ۳ tenant واجد شرایط | in-app + reviewer task؛ external پیش‌فرض خاموش | metricهای Green امنیت و حداقل ۲ workflow activated. |
| ۲. limited production | ۱۰–۲۰ tenant با opt-in | channel خارجی فقط برای tenantهای approved | ۷ روز Green عملیاتی و sign-offهای کامل. |
| ۳. broad production | cohort واجد شرایط | rollout مرحله‌ای و kill switch برقرار | ۱۴ روز Green، هیچ Red باز و SLO/owner پایدار. |

### sign-off matrix پیش از production

| sign-off | artifact لازم | معیار پذیرش | authority |
|---|---|---|---|
| Product | activation spec، UX cue و reason taxonomy | workflow کامل و criteria activation تایید شده | Head of Product |
| Security/CISO | threat model، policy matrix، key/secret boundary و negative test | صفر bypass، zero raw payload evidence، incident drill پاس | Security owner |
| Privacy/DPO یا owner معادل | consent text، data map، retention/DSR policy | telemetry/channel مجاز و revocation flow tested | Privacy owner |
| Platform/SRE | dashboard، alert، DLQ runbook، rollback/kill switch | retry/DLQ/lease/chaos test و on-call owner تایید | SRE lead |
| Engineering | schema migration، RLS، idempotency و replay test report | zero cross-tenant or duplicate effect failure | Engineering lead |
| Customer Success | playbook، escalation queue و quiet period | reviewer handoff و human override ready | CS lead |
| Finance/Deal Desk | package، pilot credit، cost-to-serve و proposal path | discount/term guardrail و owner اقتصادی روشن | Finance + Sales |
| مشتری: data/security owner | data boundary و channel approval | policy approval مکتوب | Customer owner |
| مشتری: economic sponsor | pilot success metric و decision date | budget/procurement path مشخص | Economic sponsor |

### تصمیم Green برای full production

گسترش به production فقط وقتی Green است که تمام sign-offهای لازم ثبت شده باشد، هیچ Red باز وجود نداشته باشد، policy bypass و cross-tenant failure برابر صفر باشد، duplicate effect صفر باشد، kill switch و rollback در drill اثبات شده باشند، Outbox و activation metricها به مدت دست‌کم ۱۴ روز پایدار باشند و cohort کاربرد واقعی/qualified، هدف‌های activation را برآورده کند. Yellow تنها اجازهٔ cohort محدود و time-boxed می‌دهد؛ هر Yellow باید owner و تاریخ رفع داشته باشد. هر Red شامل privacy/security incident، consent bypass، tenant isolation failure، duplicate external effect، rollback غیرقابل‌اجرا یا نبود owner اقتصادی، rollout را متوقف می‌کند.

## ۶. Alertها و runbookهای حداقلی

| alert | severity پیشنهادی | اقدام اول | owner |
|---|---|---|---|
| `activation_policy_bypass` یا raw payload detection | Critical | kill switch global، revoke channel credential، incident response | Security + SRE |
| cross-tenant or recipient mismatch | Critical | stop external delivery، preserve audit، notify security | Security |
| outbox oldest pending > ۱۵ دقیقه | High | worker health/lease/DLQ triage | SRE |
| dead event rate > ۱٪ | High | pause channel/route، classify stable error codes | SRE + Engineering |
| opt-out یا unwanted-trigger > ۳٪ | High | pause trigger version، CS outreach و UX review | Product + CS |
| activation completion Red | Medium | inspect funnel / reason taxonomy و run experiment | Product |

## منابع داخلی

[1] `enterprise_control_plane/app/outbox.py`.

[2] `GTM_PILOT_AND_MEASUREMENT_PLAN_FA.md`، بخش instrumentation و حریم خصوصی.

[3] `enterprise_control_plane/app/repositories.py`، `record_quality_gate_observation` و `enqueue_outbox_event`.

[4] `enterprise_control_plane/app/metrics.py`.
