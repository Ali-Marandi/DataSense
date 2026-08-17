# Runbook On-Call و آستانه‌های Alert برای Activation Limited Production

## ۱. هدف، scope و قاعدهٔ عملیاتی

این runbook فقط برای cohort محدود، opt-in و دارای sign-off Activation استفاده می‌شود. هدف on-call، حفاظت از consent، policy و اثر خارجی است؛ نه بهینه‌سازی تعداد notification یا پنهان‌کردن lag. وقتی safety و throughput با هم تعارض دارند، **safety اولویت دارد**.

> قاعدهٔ عملیاتی: اگر on-call نتواند در کمتر از پنج دقیقه ثابت کند delivery خارجی مجاز است، باید delivery خارجی activation را pause/suppress کند و به‌جای آن، audit و cue داخلیِ از پیش‌تأییدشده را نگه دارد.

این runbook تا زمان افزودن metricهای activation به application و deploy شدن dashboard/PrometheusRule، یک **gate اجرای عملیاتی** است. PromQLهای activation نباید پیش از وجود source metric در production/staging فعال شوند.[1]

## ۲. پیش‌نیازهای شروع Limited Production

| گیت | شرط لازم | owner | evidence |
|---|---|---|---|
| Cohort | tenantهای synthetic/design-partner opt-in و allow-list ثبت شده‌اند | Product + CS | cohort record |
| External delivery | fake provider در staging؛ channel واقعی فقط پس از policy approval | Security + Privacy | channel decision |
| Circuit | global و tenant kill switch، Open/Half-Open/Close و audit قابل‌استفاده‌اند | SRE + Security | drill record |
| Observability | metrics، dashboards، alert routing و pager test فعال‌اند | SRE | screenshot / Alertmanager test |
| On-call | primary، secondary و Security contact برای change window مشخص‌اند | SRE | rotation + escalation matrix |
| Runbooks | lag، dead letter، revocation، provider outage و rollback runbook reviewed هستند | SRE + Engineering | sign-off |
| Evidence | P0 chaos scenarios PASS در staging یا risk acceptance مکتوب وجود دارد | Release Owner | validation report |

اگر هر ردیف بالا Red باشد، limited production آغاز نمی‌شود. Yellow فقط با owner، due date و approval Release Owner + Security ممکن است و external channel scope باید محدودتر شود.

## ۳. نقش‌ها، Pager و زمان پاسخ

| severity | مثال | primary route | acknowledgement | containment target | escalation |
|---|---|---|---:|---:|---|
| **P1 / Critical** | compliance violation، kill switch failure، recipient/cross-tenant risk، lag >15m، worker unavailable | SRE primary + Security | 5 دقیقه | 10 دقیقه | Incident Commander در 10 دقیقه؛ Privacy در رخداد consent/data؛ Engineering در 15 دقیقه |
| **P2 / High** | lag >5m، dead ratio >1٪، revocation slow، payload rejection burst | SRE primary | 15 دقیقه | 30 دقیقه | Engineering/Security/Privacy بنا بر reason code |
| **P3 / Warning** | denial spike، blocked spike، funnel stalled | Product/CS یا SRE بنا بر rule | 1 ساعت در window rollout | تا پایان shift | Release Owner اگر روند پایدار ماند |
| **P4 / Informational** | expected suppression، canary completion، config deploy audit | dashboard/release channel | بدون pager | review روزانه | — |

**ممنوعیت ارتباط:** Alertmanager نباید مستقیماً برای مشتری message ارسال کند. هر customer communication پس از triage و تأیید Customer Success + Security/Privacy مرتبط انجام می‌شود.

## ۴. checklist آغاز shift و release window

### آغاز shift

- [ ] dashboardهای Reliability & Lag، Compliance & Policy و Release Readiness باز هستند.
- [ ] `datasense_activation_kill_switch_state` و circuit audit state با change plan مطابقت دارد.
- [ ] worker health، readiness، metrics scrape و replica count Green هستند.
- [ ] queue age، pending، dead، lease recovery و throughput baseline قبل از تغییر snapshot شده‌اند.
- [ ] primary/secondary on-call، Security delegate و Release Owner در channel incident اعلام شده‌اند.
- [ ] policy version، activation version، image digest و cohort allow-list در change record ثبت شده‌اند.
- [ ] no raw payload logging policy و access boundaries توسط on-call یادآوری شده‌اند.

### آغاز release/canary

- [ ] فقط synthetic یا allow-listed cohort فعال است.
- [ ] external channel rate cap و quiet period مطابق release plan هستند.
- [ ] fake provider یا approved sandbox در staging استفاده می‌شود.
- [ ] dashboard refresh 30s است و alert routing test شده است.
- [ ] rollback target digest و migration compatibility evidence در change record موجود است.
- [ ] circuit `CLOSED` فقط پس از sign-off معتبر است؛ هیچ SQL update یا bypass مستقیم مجاز نیست.

## ۵. آستانه‌های alert اولیه برای Limited Production

این اعداد **آستانهٔ عملیاتی اولیه برای cohort محدود** هستند، نه SLO قراردادی یا baseline نهایی. پس از حداقل ۱۴ روز evidence پایدار و حجم کافی، SRE/Product/Security باید آن‌ها را calibrate کنند.

| alert | expression / signal | for | severity | auto-action | human first action |
|---|---|---:|---|---|---|
| `ActivationComplianceViolation` | `sum(increase(datasense_activation_compliance_violations_total[5m])) > 0` | 0m | P1 | global circuit Open + external channel pause | Security verifies no bypass; SRE captures audit/metrics. |
| `ActivationRevocationSlow` | `p95(datasense_activation_revocation_enforcement_seconds) > 300` | 5m | P1 | tenant/global external pause for affected scope | Privacy checks revocation path/cache; SRE checks worker. |
| `OutboxCriticalLag` | `max(datasense_outbox_oldest_pending_age_seconds) > 900` | 2m | P1 | circuit Open; freeze activation release | SRE health/DB/provider triage; Security verifies zero external effect. |
| `ActivationWorkerUnavailable` | `min(up{job=~".*outbox.*"}) == 0` | 2m | P1 | external pause if no healthy worker | SRE restore deployment/probe; do not bypass queue. |
| `OutboxLagElevated` | `max(datasense_outbox_oldest_pending_age_seconds) > 300` | 5m | P2 | none; prepare pause if trend rises | inspect throughput, locks, provider latency, queue ownership. |
| `ActivationDeadDeliveryRateHigh` | `dead / (sent+retry+dead) > 0.01` over 15m | 10m | P2 | route-specific pause if error is provider/config | classify stable code; no redrive without ticket/audit. |
| `ActivationPayloadRejectionsBurst` | `sum(increase(datasense_activation_payload_rejections_total[5m])) > 5` | 5m | P2 | freeze producer/release version | Security/Engineering inspect schema and logs without payload. |
| `ActivationPolicyDenialSpike` | denial ratio >25% and decisions >20 over 15m | 15m | P3 | none | Privacy/Product compare consent/policy/config release. |
| `ActivationExternalBlockedSpike` | `sum(increase(datasense_activation_external_delivery_blocked_total[15m])) > 10` | 15m | P3 | none | inspect recipient/config; suppression is not bypassed. |
| `ActivationRetryRatioHigh` | `retry / (sent+retry+dead) > 0.20` over 15m | 10m | P2 | provider route pause if error trend persists | provider status + circuit/policy check. |
| `ActivationLeaseRecoveryLoop` | `sum(increase(datasense_outbox_lease_recoveries_total[15m])) > 3` | 5m | P2 | none | worker crash/lease length analysis; avoid parallel restarts. |
| `ActivationFunnelStalled` | state age >86400s for eligible/contract states | 30m | P3 | none | Product/CS human follow-up; no forced notification. |
| `KillSwitchUnexpectedState` | state differs from approved change-window state | 1m | P1 if unexpected Open/Close risk; P2 otherwise | freeze release | Security/SRE validate actor and audit state. |

### PromQL notes

برای `p95` revocation از expression استاندارد histogram استفاده کنید:

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(datasense_activation_revocation_enforcement_seconds_bucket[15m])
  )
) > 300
```

برای dead/retry ratio از `clamp_min` استفاده کنید تا در حجم نزدیک صفر false positive ایجاد نشود:

```promql
sum(rate(datasense_activation_trigger_outcomes_total{outcome="dead"}[15m]))
/
clamp_min(sum(rate(datasense_activation_trigger_outcomes_total{outcome=~"sent|retry|dead"}[15m])), 1)
> 0.01
```

## ۶. پاسخ گام‌به‌گام به incidentهای اصلی

### P1-A — Compliance violation یا attempted policy bypass

**Trigger:** هر افزایش `datasense_activation_compliance_violations_total`.

1. در پنج دقیقه اول، circuit global را از مسیر approved controller روی `OPEN` یا `MANUAL_KILL` قرار دهید؛ اگر automation همین کار را کرده، audit state را تأیید کنید.
2. external delivery count را از لحظهٔ alert بررسی کنید؛ انتظار `0` است.
3. Security، SRE و Incident Commander را وارد کنید؛ Privacy اگر consent/data boundary مرتبط است افزوده شود.
4. rollout/version را freeze کنید؛ هیچ retry/redrive یا database update مستقیم انجام ندهید.
5. artifactهای redacted شامل alert, circuit audit, metric snapshot, image digest, policy version و deployment revision را ذخیره کنید.
6. اگر attempted effect یا cross-tenant/recipient risk مشاهده شد، incident `Red` می‌ماند و customer communication فقط با approval انجام می‌شود.

**Exit:** Security approval، no further violation، root-cause CAPA owner/date، kill switch drill evidence و decision record.

### P1-B — Outbox critical lag بیش از ۱۵ دقیقه

1. circuit باید `OPEN` شود؛ external activation delivery را pause کنید.
2. pending events دورهٔ incident را redrive نکنید؛ final suppression یا fresh eligibility evaluation لازم است.
3. SRE: worker readiness/replicas، DB pool/lock wait، oldest age، queue status، provider latency، lease recovery و rollout revision را بررسی کند.
4. Security: policy re-check behavior، provider-call count پس از Open و kill-switch availability را تأیید کند.
5. Engineering: correlation با migration/config/release را بررسی کند؛ rollback فقط با compatibility review و approval SRE+Security انجام شود.
6. Half-Open فقط پس از lag کمتر از ۳۰۰ ثانیه برای ۱۵ دقیقه، healthy worker، zero compliance violation و canary approval قابل‌اجراست.

### P1-C — Worker unavailable

1. external activation را pause کنید؛ worker را با bypass کردن readiness یا حذف policy restart نکنید.
2. `kubectl get pods`, readiness events و ServiceMonitor/metrics target را به‌صورت read-only بررسی کنید.
3. اگر rollout جدید عامل است، deployment revision و migration compatibility را review کنید؛ rollback مطابق change record است.
4. بعد از restore worker، queue را مشاهده کنید اما external messageهای stale را redrive نکنید.
5. اگر lag به P1 رسید، runbook P1-B برتری دارد.

### P2-A — Dead ratio یا retry ratio بالا

1. route/error code bounded را گروه‌بندی کنید؛ raw provider response یا recipient را در incident channel نگذارید.
2. اگر provider/config failure مشترک است، route خارجی را pause و incident را به Engineering/SRE route کنید.
3. dead event بدون ticket و approval Security/SRE redrive نمی‌شود.
4. پس از fix، fake provider/staging test باید behavior retry/dead را تأیید کند؛ سپس فقط fresh eligibility evaluation برای trigger جدید انجام می‌شود.

### P2-B — Revocation slow یا payload rejection burst

**Revocation slow:** external channel scope را pause کنید، Privacy owner را page کنید، cache/policy propagation و worker backlog را بررسی کنید. Exit فقط با p95 زیر ۵ دقیقه و test evidence است.

**Payload rejection burst:** producer/release version را freeze کنید، validation schema و event type allow-list را بررسی کنید، log capture redacted انجام دهید و outbox insertion count را کنترل کنید. هدف، دورزدن validator برای «حفظ throughput» نیست.

### P3 — Policy denial/blocked spike یا funnel stall

1. suppression را به‌عنوان failure خودکار تلقی نکنید؛ reason taxonomy و release/policy/consent change را بررسی کنید.
2. اگر privacy/config cause تأیید شد، trigger version pause و P2/P1 escalation را اعمال کنید.
3. اگر customer-fit/friction cause است، Product/CS یک human review انجام می‌دهند؛ frequency افزایش داده نمی‌شود.
4. Trend، decision و CAPA در daily review ثبت شود.

## ۷. Circuit و rollback operations

| عملیات | چه کسی | کنترل | هرگز انجام ندهید |
|---|---|---|---|
| Open circuit | automation معتبر یا SRE/Security owner | correlation ID + audit + alert | direct DB mutation یا provider-side workaround |
| Manual Kill | Security/SRE authorized owner | dual acknowledgement در P1 | close کردن صرفاً برای کاهش alert noise |
| Half-Open | SRE + Security | canary ≤5/min، 15m، health evidence | full traffic restore یا unknown recipient |
| Close | SRE + Security + Product | lag/health/compliance/canary sign-offs | auto-close پس از کاهش لحظه‌ای lag |
| Rollback revision | SRE workflow | change record و migration compatibility | rollback بدون Open/freeze یا redrive stale event |
| Redrive | ticketed workflow پس از Security/SRE review | fresh eligibility mandatory | replay خودکار پیام قدیمی |

## ۸. daily operating cadence و release reporting

### در طول Limited Production

| cadence | owner | خروجی لازم |
|---|---|---|
| شروع هر shift | SRE on-call | baseline snapshot، kill switch/circuit state، primary/secondary check. |
| هر release/canary | Release Owner | digest/policy/cohort/change record و rollback target. |
| پس از هر P1/P2 | Incident Commander | timeline، evidence card، CAPA owner/date و sign-off. |
| daily review | Product + SRE + Security + CS | dashboard trend، denial reasons، queue health، open Yellow/Red. |
| weekly gate review | Release Owner + seven stakeholders | cohort change/pause decision و threshold calibration proposal. |

### template incident update داخلی

```markdown
[ACTIVATION INCIDENT UPDATE #<id> · <UTC>]
Severity: P1/P2/P3
Scope: activation only / external channel paused? <yes/no>
Safety state: circuit=<state>, kill-switch=<state>
Observed signal: <alert + bounded metric>
Customer impact: <aggregate / unknown / none observed>
Actions completed: <Open/freeze/triage/rollback>
Actions in progress: <owner + ETA>
Do not do: no direct DB edits, no raw payload, no stale redrive
Next update: <UTC>
```

## ۹. خروج از Limited Production یا گسترش cohort

| تصمیم | شرط |
|---|---|
| ادامهٔ cohort محدود | هیچ P1 باز، dashboard Green/Yellow قابل‌توضیح، CAPAهای P0 در مسیر. |
| pause | P1، kill-switch/circuit uncertainty، policy bypass، recipient/tenant isolation risk یا alert routing failure. |
| افزایش cohort | حداقل ۱۴ روز evidence پایدار، P0 scenario PASS در staging، zero critical finding باز، seven sign-offهای لازم و capacity review. |
| Broad Production | تمام C03–C16 staging PASS، alert threshold calibration، rollback drill PASS و governance evidence کامل. |

## منابع داخلی

[1] `ACTIVATION_OBSERVABILITY_ALERTS_AND_INTERNAL_SIGNOFF_RUNBOOK_FA.md`.

[2] `ACTIVATION_OUTBOX_CIRCUIT_BREAKER_AND_CHAOS_TEST_PLAN_FA.md`.

[3] `ACTIVATION_CHAOS_POST_INCIDENT_AND_VALIDATION_REPORT_TEMPLATE_FA.md`.

[4] `ACTIVATION_CHAOS_REMEDIATION_AND_PASS_CONVERSION_PLAN_FA.md`.
