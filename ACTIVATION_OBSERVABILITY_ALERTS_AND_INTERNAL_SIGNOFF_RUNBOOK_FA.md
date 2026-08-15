# Runbook داشبورد، هشدار و Sign-off داخلی برای Activation Outbox

## هدف و مرز

این runbook تعیین می‌کند که پیش از activation rollout، چه telemetryی باید instrument شود، کدام dashboardها در لحظه دیده شوند، چه alertهایی به چه تیمی برسند و هر یک از هفت stakeholder داخلی با چه evidenceی sign-off بدهد. هدف از metricها، اندازه‌گیری backlog، delivery، policy denial، privacy safety و activation funnel است؛ نه پروفایل‌سازی کاربر یا انتقال دادهٔ تحلیلی.

> تمام metricهای activation باید low-cardinality باشند. `organization_id`، `account_id`، `user_id`، email، dataset، نام/URL provider، request ID، نام ستون، raw payload و exception text نباید metric label باشند.

## ۱. Instrumentation لازم پیش از فعال‌سازی alert

metricهای Outbox موجود شامل pending depth، oldest pending age، processing leases، dead events، lease recovery و delivery outcome هستند.[1] برای activation، نخست باید metricهای زیر در `metrics.py` و handlerهای policy/delivery افزوده شوند؛ تا قبل از instrumentation، Grafana و PrometheusRule نباید query ساختگی یا بدون source metric داشته باشند.

| metric پیشنهادی | نوع | labelهای مجاز | زمان increment / observe |
|---|---|---|---|
| `datasense_activation_policy_decisions_total` | Counter | `outcome`, `trigger_code`, `policy_version` | پس از evaluation policy قبل از enqueue و قبل از delivery. |
| `datasense_activation_trigger_outcomes_total` | Counter | `trigger_code`, `channel`, `outcome` | نتیجهٔ final: sent، retry، dead، suppressed یا idempotent_skip. |
| `datasense_activation_suppressions_total` | Counter | `reason_code`, `trigger_code` | consent/policy/quiet-period/template denial. |
| `datasense_activation_external_delivery_blocked_total` | Counter | `reason_code`, `channel` | جلوگیری از external effect به علت policy یا recipient. |
| `datasense_activation_payload_rejections_total` | Counter | `reason_code`, `event_type` | رد schema/allow-list قبل از write. |
| `datasense_activation_compliance_violations_total` | Counter | `violation_code` | invariant breach، مانند attempted delivery بدون policy allow؛ باید هم‌زمان kill switch بخورد. |
| `datasense_activation_kill_switch_state` | Gauge | `scope` | `global` و `tenant`؛ ۱ یعنی فعال و ۰ یعنی غیرفعال. |
| `datasense_activation_revocation_enforcement_seconds` | Histogram | `channel` | از ثبت revocation تا suppress شدن آخرین delivery eligible. |
| `datasense_activation_state_age_seconds` | Gauge | `state` | age aggregate/oldest cohort state؛ بدون account label. |
| `datasense_activation_funnel_events_total` | Counter | `stage`, `outcome` | eligible، first_trusted_report، reviewer_handoff، activated. |

`outcome`، `trigger_code`، `reason_code`، `channel`، `state` و `violation_code` باید enum نسخه‌دار و bounded باشند. استفاده از عبارت خطا یا نام tenant به‌عنوان label، هم privacy و هم کارایی Prometheus را نقض می‌کند.[2]

## ۲. dashboardهای بلادرنگ پیشنهادی

### Dashboard A — **Outbox Reliability & Lag**

این dashboard ادامهٔ dashboard فعلی Control Plane است و برای SRE/Engineering در incident استفاده می‌شود. refresh پیشنهادی ۳۰ ثانیه است، اما alert تنها با window و `for` مشخص page می‌کند تا noise ایجاد نشود.

| پنل | PromQL یا منبع | نمایش | کاربرد عملیاتی |
|---|---|---|---|
| Oldest pending age | `max(datasense_outbox_oldest_pending_age_seconds)` | time series + threshold ۵m/۱۵m | lag واقعی را از depth جدا می‌کند. |
| Queue depth by status | `max(datasense_outbox_pending_events)`, `max(datasense_outbox_processing_leases)`, `max(datasense_outbox_dead_events)` | stacked status | backlog یا worker stall. |
| Delivery outcomes | `sum by (event_type,outcome) (rate(datasense_outbox_delivery_attempts_total[5m]))` | stacked time series | delivered/retry/dead mix. |
| Dead ratio | `sum(rate(...{outcome="dead"}[15m])) / clamp_min(sum(rate(...[15m])),1)` | stat + sparkline | provider/configuration degradation. |
| Lease recovery | `sum(increase(datasense_outbox_lease_recoveries_total[15m]))` | stat | worker crash یا lease نامتناسب. |
| Worker scrape health | `min(up{job=~".*outbox.*"})` | status history | worker unavailable before queue age grows. |
| Worker throughput | `sum(rate(datasense_outbox_delivery_attempts_total{outcome="delivered"}[5m]))` | req/s | capacity/saturation analysis. |

### Dashboard B — **Activation Compliance & Policy**

این dashboard برای Security، Privacy، Product و SRE مشترک است. به‌جای نشان‌دادن مخاطب یا tenant، فقط شکل تصمیم‌های policy و اثر آن‌ها را نمایش می‌دهد.

| پنل | PromQL پیشنهادی | Green interpretation | action اگر Red شد |
|---|---|---|---|
| Policy decisions by outcome | `sum by (outcome) (rate(datasense_activation_policy_decisions_total[5m]))` | allow/suppress ratio قابل‌توضیح است. | spike outcome را با config version و release تطبیق دهید. |
| Policy denial ratio | `sum(rate(datasense_activation_policy_decisions_total{outcome=~"suppress_.*"}[15m])) / clamp_min(sum(rate(datasense_activation_policy_decisions_total[15m])),1)` | baseline ثابت بعد از rollout. | Privacy/Product review؛ check consent/config drift. |
| External delivery blocked | `sum by (reason_code,channel) (increase(datasense_activation_external_delivery_blocked_total[15m]))` | policy gate اثر دارد و reason bounded است. | misconfiguration یا recipient verification را بررسی کنید. |
| Suppressions by reason | `sum by (reason_code) (rate(datasense_activation_suppressions_total[15m]))` | quiet-period/consent reasons قابل‌انتظارند. | `policy_denied` یا `template_removed` surge نیازمند triage است. |
| Payload rejection | `sum by (reason_code,event_type) (increase(datasense_activation_payload_rejections_total[5m]))` | صفر یا نزدیک صفر بعد از hardening. | schema/producer regression یا abuse path. |
| Compliance invariant breaches | `sum(increase(datasense_activation_compliance_violations_total[5m]))` | صفر مطلق. | kill switch، incident response و forensic audit. |
| Revocation enforcement | `histogram_quantile(0.95, sum by (le) (rate(datasense_activation_revocation_enforcement_seconds_bucket[15m])))` | p95 کمتر از ۵ دقیقه. | pause external channel و بررسی cache/worker. |
| Kill-switch state | `max by (scope) (datasense_activation_kill_switch_state)` | مطابق change window. | unexpected change: Security/SRE escalation. |

### Dashboard C — **Activation Funnel & Customer Outcome**

این dashboard برای Product و Customer Success است و در کنار Dashboard B دیده می‌شود تا volume trigger با ارزش واقعی اشتباه گرفته نشود.

| پنل | منبع | interpretation |
|---|---|---|
| Funnel conversion | increaseهای `activation_funnel_events_total` به تفکیک `stage` | افت `eligible→first_trusted_report`، friction onboarding را نشان می‌دهد. |
| State age | `max by (state) (datasense_activation_state_age_seconds)` | accountهای aggregate در stateهای راکد، queue CS را تعیین می‌کنند. |
| Trigger outcome mix | `sum by (trigger_code,channel,outcome) (rate(datasense_activation_trigger_outcomes_total[15m]))` | retry/suppressed/dead را از completion واقعی جدا می‌کند. |
| In-app completion | `first_trusted_report / eligible` در cohort window | ارزش cue را با control cohort مقایسه کنید. |
| Reviewer handoff | funnel stage `reviewer_handoff` | نشان می‌دهد evidence از کاربر منفرد به workflow تیمی منتقل شده یا نه. |
| Unwanted trigger/opt-out | event bounded از preference center | اگر نسبت آن بالا رفت، trigger version را pause کنید. |

### Dashboard D — **Release & Sign-off Readiness**

این dashboard برای جلسهٔ تصمیم rollout است و traffic detail نشان نمی‌دهد. چهار tile بزرگ داشته باشد: **Security/Privacy**, **Reliability**, **Activation Outcome**, **Commercial Qualification**. هر tile باید Green/Yellow/Red باشد و به artifact یا runbook مربوط link داشته باشد.

## ۳. Alert ruleهای مشخص

thresholdها در جدول زیر **baseline اولیهٔ cohort محدود** هستند و نباید به‌عنوان SLO قراردادی یا production permanent بدون calibration تلقی شوند. ruleها پس از instrumentation در `prometheus-rules.yaml` افزوده و با Alertmanager route بر اساس `service` و `severity` هدایت شوند.

| نام alert | PromQL پیشنهادی | for | severity | گیرندهٔ اول | اقدام اول |
|---|---|---:|---|---|---|
| `DataSenseActivationComplianceViolation` | `sum(increase(datasense_activation_compliance_violations_total[5m])) > 0` | 0m | critical | Security + SRE | global kill switch، توقف channel خارجی، incident response. |
| `DataSenseActivationRevocationSlow` | `histogram_quantile(0.95, sum by (le) (rate(datasense_activation_revocation_enforcement_seconds_bucket[15m]))) > 300` | 5m | critical | Privacy + SRE | pause external delivery، بررسی cache/worker. |
| `DataSenseOutboxOldestActivationLate` | `max(datasense_outbox_oldest_pending_age_seconds) > 300` | 5m | high | SRE | worker/provider/DB triage؛ check queue ownership. |
| `DataSenseOutboxActivationCriticalLag` | `max(datasense_outbox_oldest_pending_age_seconds) > 900` | 2m | critical | SRE + Security | pause external channel، kill switch در صورت compliance impact. |
| `DataSenseActivationDeadDeliveryRateHigh` | `sum(rate(datasense_activation_trigger_outcomes_total{outcome="dead"}[15m])) / clamp_min(sum(rate(datasense_activation_trigger_outcomes_total{outcome=~"sent|retry|dead"}[15m])),1) > 0.01` | 10m | high | SRE + Engineering | classify stable error code؛ redrive فقط با ticket/audit. |
| `DataSenseActivationPayloadRejectionsBurst` | `sum(increase(datasense_activation_payload_rejections_total[5m])) > 5` | 5m | high | Security + Engineering | stop producer rollout؛ inspect schema without logging payload. |
| `DataSenseActivationPolicyDenialSpike` | `(sum(rate(datasense_activation_policy_decisions_total{outcome=~"suppress_.*"}[15m])) / clamp_min(sum(rate(datasense_activation_policy_decisions_total[15m])),1) > 0.25) and (sum(increase(datasense_activation_policy_decisions_total[15m])) > 20)` | 15m | warning | Privacy + Product | compare policy/config release and consent changes. |
| `DataSenseActivationExternalBlockedSpike` | `sum(increase(datasense_activation_external_delivery_blocked_total[15m])) > 10` | 15m | warning | Security + CS | recipient/config verification؛ no bypass. |
| `DataSenseActivationWorkerUnavailable` | `min(up{job=~".*outbox.*"}) == 0` | 2m | critical | SRE | restore worker, check deployment/readiness. |
| `DataSenseActivationFunnelStalled` | `max(datasense_activation_state_age_seconds{state=~"eligible|first_imported|contract_ready"}) > 86400` | 30m | warning | Product + CS | analyze friction; in-app cue or human intervention. |

**عدم‌ارسال مستقیم به مشتری:** alertهای بالا به on-call و role route می‌شوند، نه به channel مشتری. اطلاع‌رسانی مشتری فقط پس از triage، classification و تأیید CS/Security انجام می‌شود.

## ۴. Template ارتباطی مشترک برای sign-off

متن زیر را به‌صورت دقیق برای هر role ارسال کنید و فقط بخش **دامنهٔ اختصاصی نقش** را جایگزین کنید.

```markdown
Subject: [SIGN-OFF REQUIRED][Activation v1][<Cohort/Environment>] <Role> review by <YYYY-MM-DD>

سلام <نام/نقش>،

برای عبور Activation v1 از gate <Internal / Design Partner / Limited Production / Broad Production>، تأیید شما لازم است.

**تصمیم درخواستی:** یکی را صریحاً انتخاب کنید: `APPROVE`، `APPROVE WITH CONDITIONS`، یا `REJECT`.

**دامنهٔ تغییر:**
- Triggerهای rule-based و metadata-only برای مسیر First Trusted Report.
- delivery مبتنی بر Transactional Outbox با idempotency، retry/DLQ و policy re-check.
- اثر خارجی تنها با consent، tenant policy، recipient verification و channel allow-list مجاز است.
- در هر فقدان یا ambiguity، نتیجه `suppressed` است؛ نه retry و نه delivery خارجی.

**Cohort و زمان‌بندی:** <environment / tenant count / start / rollback window>

**Evidence برای review:**
1. <link به activation specification و policy matrix>
2. <link به dashboard و snapshot metricها>
3. <link به test report: RLS, idempotency, replay, redaction, kill-switch>
4. <link به runbook و incident/rollback plan>
5. <link به دامنهٔ اختصاصی role>

**ریسک‌های باز و تصمیم پیشنهادی:** <none یا فهرست Yellow با owner و date>

**دامنهٔ اختصاصی نقش:**
<role-specific checklist زیر>

لطفاً با قالب پاسخ زیر reply کنید:
`Decision: APPROVE | APPROVE WITH CONDITIONS | REJECT`
`Conditions / Blocking issue: ...`
`Evidence reviewed: ...`
`Owner and due date for conditions: ...`
`Name, role, date: ...`

با احترام،
<Release owner>
```

## ۵. checklist و پیام اختصاصی هفت stakeholder داخلی

### ۱) Head of Product / Product Owner

**دامنهٔ اختصاصی نقش در پیام:** «تأیید کنید state machine، copy cueها، suppression reasonها، definition activation و معیارهای Green/Yellow/Red با مسئلهٔ مشتری و cohort هم‌راستا هستند.»

| checklist Product | evidence لازم |
|---|---|
| Activation برابر با workflow کامل است، نه نصب یا تعداد event. | state-machine و UX prototype. |
| مسیر first trusted report، Contract، Gate، evidence و reviewer handoff را نشان می‌دهد. | usability session یا acceptance recording بدون data حساس. |
| trigger copy، quiet period، dismiss/pause و human handoff روشن‌اند. | copy deck و preference behaviour. |
| metricهای funnel با control cohort قابل‌مقایسه‌اند. | analytics spec و cohort definition. |
| Yellow/Redها owner و decision date دارند. | release-readiness dashboard. |

### ۲) Security Lead / CISO Delegate

**دامنهٔ اختصاصی نقش در پیام:** «تأیید کنید external effect بدون policy allow غیرممکن است و threat model، payload allow-list، key/secret boundary، invariant test و incident procedure کافی‌اند.»

| checklist Security | evidence لازم |
|---|---|
| policy pre-enqueue و re-check worker طراحی و test شده‌اند. | sequence diagram و negative tests. |
| raw payload، recipient و secret در Outbox/metric/log نیستند. | schema review، redaction test و log sampling. |
| recipient verification و channel allow-list fail-closed هستند. | test matrix و config review. |
| compliance violation، kill switch و incident route tested شده‌اند. | tabletop/drill result. |
| RLS/cross-tenant tests و dependency patch posture Green هستند. | test report و dependency scan. |

### ۳) Privacy / DPO / Privacy Owner

**دامنهٔ اختصاصی نقش در پیام:** «تأیید کنید consent، data minimization، retention، DSR و revocation enforcement با policy مشتری و دادهٔ activation سازگارند.»

| checklist Privacy | evidence لازم |
|---|---|
| event taxonomy metadata-only و purpose-limited است. | data map و event schema. |
| opt-in/opt-out، revocation و preference audit قابل‌بررسی‌اند. | flow test و audit sample. |
| revocation enforcement p95 در cohort زیر پنج دقیقه است یا Yellow owner دارد. | dashboard snapshot / test. |
| retention/deletion owner و data-subject workflow مشخص است. | policy/runbook. |
| channel خارجی و recipient country/data transfer assessment روشن است. | channel assessment یا scope exclusion. |

### ۴) Engineering Lead

**دامنهٔ اختصاصی نقش در پیام:** «تأیید کنید migration، RLS، idempotency، replay safety، API schema، policy versioning و rollback از نظر فنی آماده‌اند.»

| checklist Engineering | evidence لازم |
|---|---|
| state/audit/outbox در transaction واحد ثبت می‌شوند. | code review و integration test. |
| unique execution key، duplicate delivery و stale lease effect-free هستند. | replay/chaos test report. |
| `suppressed` از `dead` جدا و policy denial retry نمی‌شود. | state transition tests. |
| migration forward/backward compatible و rollback-tested است. | migration runbook. |
| metric labelها bounded و versioned هستند. | metrics review. |

### ۵) SRE / Platform Owner

**دامنهٔ اختصاصی نقش در پیام:** «تأیید کنید worker، dashboard، alert routing، DLQ triage، backup/restore و kill switch تحت incident قابل‌اجرا هستند.»

| checklist SRE | evidence لازم |
|---|---|
| worker health، metrics scrape و autoscaling/replica policy تعریف شده‌اند. | Kubernetes evidence و dashboard. |
| oldest pending age، dead ratio، lease recovery و policy alertها route شده‌اند. | alert test / Alertmanager route. |
| DLQ redrive نیازمند ticket/audit است و raw payload را نمایش نمی‌دهد. | runbook و access test. |
| global/tenant kill switch در drill نتیجهٔ درست می‌دهد. | drill evidence. |
| capacity، database lock و provider outage runbook تایید شده‌اند. | game-day outcome. |

### ۶) Customer Success Lead

**دامنهٔ اختصاصی نقش در پیام:** «تأیید کنید cueها مزاحم نیستند، human escalation و reviewer handoff owner دارند و account risk بدون فرستادن پیام ناخواسته مدیریت می‌شود.»

| checklist Customer Success | evidence لازم |
|---|---|
| eligible، at-risk، pause و disqualified definition برای تیم قابل‌فهم است. | playbook و training record. |
| trigger frequency، quiet period و opt-out copy تایید شده‌اند. | communication matrix. |
| reviewer handoff و escalation SLA داخلی owner دارد. | assignment matrix. |
| شکایت/opt-out taxonomy به Product و Privacy برمی‌گردد. | feedback loop. |
| اطلاع‌رسانی مشتری فقط پس از triage و approval رخ می‌دهد. | incident comms procedure. |

### ۷) Finance + Sales / Deal Desk Owner

**دامنهٔ اختصاصی نقش در پیام:** «تأیید کنید cohort و triggerها با package، pilot credit، cost-to-serve و مسیر proposal هم‌راستا هستند و activation به forecast قطعی تبدیل نشده است.»

| checklist Finance/Sales | evidence لازم |
|---|---|
| package Professional/Team/Enterprise و eligibility rule روشن است. | approved package memo. |
| annual-after-activation و Team Pilot credit، hypothesis و guardrail دارند. | pricing experiment protocol. |
| sponsor، proposal timeline و procurement owner برای cohort qualified ثبت شده‌اند. | CRM fields / mutual action plan. |
| cost-to-serve و custom support boundary before deal approval بررسی می‌شود. | deal desk checklist. |
| metric activation به‌عنوان ARR/forecast بدون paid decision ثبت نمی‌شود. | finance policy. |

## ۶. Definition of Complete برای sign-off package

یک package کامل تنها زمانی به release gate می‌رود که هر هفت approval یا approval-with-conditions دارای owner/date ثبت شده باشد، هیچ `REJECT` یا Red باز وجود نداشته باشد، conditions Yellow در release dashboard traceable باشند، و release owner نسخهٔ دقیق policy، dashboard، runbook و test evidence را در یک decision record ثبت کرده باشد. reply شفاهی یا reaction پیام، sign-off محسوب نمی‌شود.

## منابع داخلی

[1] `enterprise_control_plane/app/metrics.py` و `enterprise_control_plane/app/outbox.py`.

[2] `enterprise_control_plane/k8s/monitoring/prometheus-rules.yaml` و `grafana-dashboard.json`.

[3] `ACTIVATION_OUTBOX_FAIL_CLOSED_PRODUCTION_ROLLOUT_GUIDE_FA.md`.
