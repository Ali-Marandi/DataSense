# برنامهٔ پیاده‌سازی P1/P2 و بستهٔ Evidence برای Activation Chaos

**نویسنده:** Manus AI
**دامنه:** DataSense Activation Governance
**وضعیت سند:** طراحی اجرایی برای `protected staging`؛ مجوز اجرای production نیست.
**Baseline:** C03/C09/C10 برابر `PARTIAL`، C05/C08/C11/C13/C14/C15/C16 برابر `NOT RUN` و هیچ `FAIL` مشاهده‌شده‌ای ثبت نشده است.[1]

> آزمون unit یا synthetic فقط **`PASS — model`** محسوب می‌شود. تبدیل به **`PASS — staging`** تنها بعد از اجرای isolated با tenant مصنوعی، fake provider، ثبت زمان UTC، نسخه‌ها، متریک‌های redacted، شمارش اثر خارجی و sign-off امکان‌پذیر است.[2]

## 1. وضعیت و ترتیب تصمیم‌گیری

| Gate | سناریو | هدف | محیط مجاز | خروجی لازم |
|---|---|---|---|---|
| G2 | C09، C10 | اثبات retry و DLQ governed با fake provider | integration isolated | artifact آزمون، reason code و call count |
| G3 | C03، C05، C08، C09، C10، C11، C13، C14 | اثبات end-to-end کنترل‌های fail-closed | protected staging | evidence card تکمیل‌شده برای هر سناریو |
| G4 | C15، C16 | game day ظرفیت/lag و rollback واقعی staging | protected staging | evidence card، graph و change/rollback artifact |

هیچ سناریویی صرفاً به‌دلیل وجود کد یا PASS در CI نباید `PASS — staging` یا production-ready خوانده شود. CI باید فقط آزمون deterministic، lint، integrity و guard غیرتولیدی را اجرا کند؛ pod kill، flood و provider delivery واقعی خارج از CI و صرفاً با change approval در staging انجام می‌شوند.[1]

## 2. سناریوهای P1/P2 باقی‌مانده و پیاده‌سازی پیشنهادی

### C09 — timeout و خطای 5xx provider؛ retry bounded و circuit-aware

**هدف.** یک timeout یا پاسخ `5xx` provider نباید retry نامحدود، دورزدن policy، یا delivery جدید پس از Open شدن circuit ایجاد کند. هر retry باید مجدداً policy، consent، kill switch و state circuit را بررسی کند.

| لایه | تغییر لازم | قرارداد fail-closed |
|---|---|---|
| `app/outbox_delivery.py` | classifier صریح برای timeout، transport و `5xx` به stable codeهای `webhook_timeout`، `webhook_transport_error` و `webhook_http_5xx` | متن exception و body provider هرگز ذخیره/label نمی‌شود. |
| `app/outbox.py` | `retry_budget` جداگانه برای activation، backoff با cap و re-check کامل `policy_evaluator` پیش از هر provider call | اگر state circuit `OPEN/MANUAL_KILL/UNKNOWN` شود، event به `suppressed` نهایی می‌رود، نه retry. |
| `app/repositories.py` و schema | ثبت bounded `retry_count`، `last_retry_reason_code` و audit transition بدون payload | transition باید owner lease را verify کند. |
| `tests/test_activation_retry_governance.py` | fake provider با sequence `timeout → 503 → success` و sequence `timeout → circuit open → suppressed` | counts و stateها deterministic باشند. |

**پروتکل آزمون integration.** یک event کاملاً synthetic با provider fake ثبت می‌شود. fake provider در دو attempt نخست به ترتیب timeout و `503` برمی‌گرداند. worker باید حداکثر مطابق `retry_budget` retry کند؛ هیچ attempt نباید policy re-check را bypass کند. پیش از attempt بعدی circuit عمداً Open می‌شود و assertion می‌گوید fake provider پس از زمان Open شمارش جدید ندارد.

| معیار PASS C09 | مقدار مورد انتظار |
|---|---|
| reason codeهای ثبت‌شده | فقط enumهای bounded؛ بدون متن exception یا URL |
| retry | حداکثر budget پیکربندی‌شده و با backoff محدود |
| پس از Open | `suppressed_circuit_open` و zero provider call بعد از UTC Open |
| audit/metric | retry counter، suppression counter و transition audit دارای correlation/version redacted |

**پیشنهاد اولیهٔ staging.** `retry_budget=3` در بازهٔ ۱۵ دقیقه برای activation external channel، base backoff پنج ثانیه و cap ۹۰۰ ثانیه. این مقدار یک guard آزمایشی است، نه SLO یا تنظیم نهایی مشتری؛ قبل از Limited Production باید با evidence ظرفیت و رفتار provider کالیبره شود.

### C10 — خطای permanent 4xx، DLQ و redrive ticketed

**هدف.** خطاهای `4xx` غیرقابل‌retry باید به `dead` دارای reason code پایدار بروند. redrive خودکار برای notification خارجی ممنوع است؛ redrive تنها با مجوز، ticket، policy re-evaluation و trigger جدید انجام می‌شود.

| لایه | تغییر لازم | قرارداد fail-closed |
|---|---|---|
| `app/outbox_delivery.py` | classifier `4xx` به `permanent_failure`، با استثنای duplicate-idempotency که provider صریحاً مستند کرده است | پاسخ provider ثبت نمی‌شود. |
| schema | جدول `activation_redrive_requests` با `organization_id`، `original_event_id_hash`، `ticket_reference`، approver، policy version و state | unique برای ticket/original-event، RLS tenant-scoped و retention metadata-only. |
| API/service | permission مستقل `activation.redrive`; approval دو-نفره Engineering/SRE یا Security برای external channel | درخواست بدون ticket/approval برابر deny است و event جدید نمی‌سازد. |
| worker | redrive، event اصلی را revive نمی‌کند؛ فقط پس از eligibility تازه یک execution key و idempotency key جدید می‌سازد | consent revoked، kill/circuit Open یا policy unknown باید redrive را suppress کند. |
| tests | unauthorized redrive، authorized ticketed redrive، revoked-consent redrive و absence of raw payload | اثر provider فقط برای trigger تازه و مجاز قابل‌مشاهده است. |

| معیار PASS C10 | مقدار مورد انتظار |
|---|---|
| 400/422 fake provider | state `dead` با reason code bounded |
| redrive بدون permission/ticket | deny و zero insert/zero provider call |
| redrive با approval اما consent revoked | `suppressed_consent_revoked`، نه redrive خارجی |
| redrive مجاز | event جدید با execution key جدید، audit ticket و policy version |

### C15 — flood synthetic، lag critical و circuit Open

**هدف.** زیر بار کنترل‌شده، صف باید bounded بماند؛ رسیدن oldest pending age به آستانهٔ critical باید alert امضاشده تولید و circuit را Open کند. از لحظهٔ Open به بعد هیچ external effect جدید مجاز نیست.

| مؤلفه | پیاده‌سازی staging-only | guard اجباری |
|---|---|---|
| synthetic generator | اسکریپت جداگانه با `--environment=staging`، tenant مصنوعی و `--confirm-nonprod` | اگر environment غیر از staging/test، fake provider یا acknowledgement نامعتبر باشد exit non-zero. |
| event cap | `--max-events` bounded، default کوچک، rate محدود و timebox | هیچ access به cohort/customer/provider واقعی. |
| fake provider | latency injection، `429`/`503` قابل‌برنامه‌ریزی و idempotency recorder | host allow-list و عدم خروج از namespace/endpoint مصنوعی. |
| monitoring | graph pending age، processing leases، retries، dead ratio، suppressions و fake-provider count | labelها بدون tenant، recipient یا payload. |
| controller | Alertmanager fake/staging با HMAC یا mTLS به `/internal/v1/activation/alerts` | فقط Open؛ close/rollout/provider action از webhook ممنوع. |

آستانهٔ اولیهٔ game day، **oldest pending age بیش از ۹۰۰ ثانیه برای دو دقیقه** است. در این وضعیت circuit باید Open و release activation freeze شود. recovery فقط بعد از pending age کمتر از ۳۰۰ ثانیه برای ۱۵ دقیقه، worker سالم، روند dead پایدار، صفر compliance violation پس از Open و approval SRE/Security مجاز است.[3]

| معیار PASS C15 | مقدار مورد انتظار |
|---|---|
| تولید synthetic | فقط tenant/fixture اجازه‌داده‌شده، count کمتر یا برابر cap |
| lag critical | state audit برای Open و alert signature معتبر |
| پس از Open | fake-provider external effect count افزایشی ندارد |
| duplicate | unique execution ledger مانع اثر تکراری است |
| observability | graph بازهٔ UTC، metrics redacted و pager/ack route ثبت شده |

### C16 — migration compatibility و rollback drill

**هدف.** rollback deployment یا migration نباید circuit state، execution ledger یا isolation tenant را از بین ببرد و نباید schema/data loss ایجاد کند. C16 شرط Broad Production است، حتی اگر تمام سناریوهای دیگر PASS staging باشند.

| گام | پیاده‌سازی/آزمون | invariant |
|---|---|---|
| preflight | schema compatibility check، immutable image digest، backup/restore point و Green probes | migration reversible یا explicitly forward-compatible باشد. |
| migration | migration روی staging isolated اجرا شود؛ circuit Open و execution ledger seeded synthetic باشند | rows و RLS policyها بعد از migration باقی بمانند. |
| rollback | deployment image به revision قبلی برگردد؛ migration rollback فقط اگر approved و data-safe است | circuit state/approval و execution state حفظ شود. |
| post-check | readiness/liveness، policy/consent query، claim/lease و fake-provider idempotency probe | data loss، cross-tenant read یا external call جدید نباشد. |

| معیار PASS C16 | مقدار مورد انتظار |
|---|---|
| circuit state | Open/approval/version قبل و بعد از undo برابر یا سازگار است |
| ledger | execution key و terminal state بدون duplicate provider effect حفظ می‌شوند |
| RLS | credential/context tenant A به state tenant B دسترسی ندارد |
| probes | ready/live، policy denial، migration checksum و fake-provider count Green هستند |
| sign-off | Engineering + SRE + Security؛ Privacy در صورت تغییر data boundary |

## 3. جزئیات آزمون‌های synthetic اجراشده برای P0

این آزمون‌ها در commit `2f64f9b` اضافه شده‌اند. اجرای کامل repository برابر **101 passed** بوده و CI commit نیز success شده است. هر ردیف زیر evidence **model** است، نه staging.[4]

| سناریو | فایل و test | fixture/محرک | assertionهای دقیق | سطح evidence فعلی |
|---|---|---|---|---|
| C03 | `test_activation_governance_p0.py::test_c03_half_open_requires_approval_is_rate_limited_and_persists` | circuit `CLOSED → OPEN`، approval synthetic و شش attempt در یک minute window | approval برای Half-Open، پنج attempt مجاز، attempt ششم `suppressed_half_open_rate_limited`، state بعد از restart abstraction باقی و close با `health_proven=False` رد | `PASS — model` |
| C05 | `...::test_c05_revocation_after_claim_suppresses_without_provider_effect` | event synthetic claimed، consent=false درست پیش از delivery | provider fake call count برابر صفر و Outbox `suppressed_consent_revoked` | `PASS — model` |
| C08 | `...::test_c08_recovered_execution_with_effect_ledger_skips_provider_duplicate` | execution ledger از پیش `effect_recorded` و replacement worker | provider fake call count صفر و event به `sent` ack می‌شود | `PASS — model` |
| C11 | `...::test_c11_schema_firewall_rejects_raw_like_payload_without_echoing_it` | unknown field شامل email-like value | `unknown_field`، عدم echo در exception؛ schema firewall پیش از enqueue | `PASS — model` |
| C13 | `...::test_c13_tenant_kill_is_isolated_and_unknown_tenant_fails_closed` | org A kill=true، org B=false و org C unprovisioned | A suppress، B allow و C fail-closed suppress؛ metric بدون tenant label | `PASS — model` |
| C14 | `test_activation_controller_auth.py::{two tests}` | alert canonical signed، replay، signature forged و timestamp stale | valid alert فقط Open؛ replay=409؛ forged=401؛ stale=401؛ close/provider operation وجود ندارد | `PASS — model` |

برای مشاهده/بازاجرای صرفاً local synthetic suite از این selection استفاده می‌شود؛ اجرای آن هیچ provider، Kubernetes یا tenant واقعی را هدف نمی‌گیرد:

```bash
cd /home/ubuntu/datasense
python3 -m pytest -q \
  enterprise_control_plane/tests/test_activation_governance_p0.py \
  enterprise_control_plane/tests/test_activation_controller_auth.py
```

## 4. طراحی Evidence Collection

### 4.1 مرز و chain of custody

هر game day باید با change ticket، execution owner، environment allow-list و acknowledgement صریح non-production آغاز شود. fixture فقط شامل opaque identifierها و tenant مصنوعی است. هیچ customer payload، provider URL، credential، raw exception، email یا identifier خام داخل evidence card، dashboard screenshot یا ticket قرار نمی‌گیرد.[2]

| artifact | روش جمع‌آوری | کنترل محرمانگی | نگهداری پیشنهادی |
|---|---|---|---|
| Manifest/version | commit SHA، immutable image digest، policy/migration version و Kustomize render hash | نسخه‌ها مجاز؛ secret ممنوع | evidence bundle همان سناریو |
| Timeline | UTC start/claim/fault/open/recovery/end | correlation ID hash، نه identifier خام | evidence card + audit export |
| Metrics | snapshot/redacted export از pending age، retries، dead، suppressions، lease recovery و provider count | label کم‌کاردینال؛ tenant/recipient/payload ممنوع | PNG/JSON signed evidence bundle |
| State/audit | circuit transitions، Outbox final state aggregate، approval/ticket ID و audit UUID/hash | reason code bounded؛ body/payload ممنوع | append-only audit export |
| External effect | fake-provider aggregate count و idempotency records | endpoint/headers/body ممنوع | fake-provider report |
| Review | Engineering/SRE/Security و Privacy اگر data boundary درگیر است | نام/role قابل‌ثبت؛ secret ممنوع | evidence card امضاشده |

پیشنهاد می‌شود همه artifactها در یک **Signed Evidence Bundle** با canonical manifest، SHA-256 file hash و HMAC موجود پروژه بسته‌بندی شوند. verification نتیجهٔ bundle و HMAC key identifier در evidence card درج شود، اما خود secret هرگز درج نشود.

### 4.2 ترتیب اجرای staging

| ترتیب | کنترل | شرط عبور |
|---|---|---|
| 0 | preflight | staging allow-list، fake provider، synthetic tenant، on-call و rollback target تأیید شدند. |
| 1 | P0 safety | C03/C05/C08/C11/C13/C14 به‌ترتیب اجرا و cardهای جداگانه ثبت شوند. |
| 2 | resilience | C09 و C10 فقط بعد از PASS staging P0 اجرا شوند. |
| 3 | load | C15 با timebox و event cap؛ در breach circuit Open/kill switch containment اولویت دارد. |
| 4 | rollback | C16 با migration-compatible revision و Green probes اجرا شود. |
| 5 | decision | reviewerها فقط بر اساس cardهای کامل وضعیت را به `PASS — staging` تبدیل کنند. |

## 5. Evidence Cardهای آمادهٔ تکمیل برای P0

> کارت‌ها عمداً خالی از مقادیر ساختگی‌اند. مقدار واقعی فقط پس از اجرای protected staging ثبت می‌شود.

### Card C03 — Half-Open canary

| Field | Record |
|---|---|
| Report ID | `ACT-CHAOS-YYYYMMDD-C03` |
| Environment / UTC | `staging` / `<start-end UTC>` |
| Commit / image / policy / migration | `<SHA / digest / versions>` |
| Fixture | `<synthetic tenant + opaque execution refs>` |
| Fault | Open circuit، approval synthetic، six canary attempts در 60s |
| Expected | 5 external fake-provider attempts حداکثر؛ ششم `suppressed_half_open_rate_limited`؛ close بدون health/approval رد |
| Required evidence | approval audit، circuit version trace، probe counter، fake-provider count و metrics snapshot |
| PASS rule | state persisted بعد از worker/controller restart و تمام invariantها برقرار |

### Card C05 — Consent revoke after claim

| Field | Record |
|---|---|
| Report ID | `ACT-CHAOS-YYYYMMDD-C05` |
| Fault | claim event synthetic، revoke consent قبل از adapter call، سپس resume worker |
| Expected | Outbox `suppressed` با `suppressed_consent_revoked`؛ fake-provider count=0 |
| Required evidence | claim/revoke/resume UTC timeline، policy version، final state aggregate، suppression metric و audit ID |
| PASS rule | retry/DLQ/fallback ایجاد نشده و raw recipient/payload در artifacts نیست |

### Card C08 — Pod kill / lease recovery

| Field | Record |
|---|---|
| Report ID | `ACT-CHAOS-YYYYMMDD-C08` |
| Fault | kill کنترل‌شدهٔ worker staging پس از claim در checkpoint مصوب؛ lease expiry؛ replacement worker |
| Expected | execution ledger یک terminal row؛ fake-provider count دقیقاً 1 یا با circuit Open برابر 0؛ manual DB fix=0 |
| Required evidence | pod event، lease-recovery metric، ledger aggregate، provider idempotency count، final Outbox state |
| PASS rule | duplicate effect و cross-tenant access صفر؛ worker health بازیابی شده است |

### Card C11 — Schema firewall / redaction proof

| Field | Record |
|---|---|
| Report ID | `ACT-CHAOS-YYYYMMDD-C11` |
| Fault | event synthetic با unknown/raw-like fieldهای email/path/URL/dataset token |
| Expected | pre-enqueue reject، Outbox insert=0، reason code bounded |
| Required evidence | rejected request/result code، DB aggregate count، redacted captured logs و `/metrics` snapshot |
| PASS rule | هیچ raw fixture value در log/metric/evidence؛ release producer frozen تا رفع deviation در صورت violation |

### Card C13 — Tenant kill switch / RLS

| Field | Record |
|---|---|
| Report ID | `ACT-CHAOS-YYYYMMDD-C13` |
| Fault | tenant synthetic A kill=true؛ B healthy؛ read/update negative test با context A علیه B |
| Expected | A suppress؛ B فقط طبق policy مجاز؛ read/update B توسط A deny/zero-row |
| Required evidence | kill version/audit، A/B fake-provider aggregates، RLS negative-query result، metrics بدون tenant label |
| PASS rule | isolation در DB و application هر دو برقرار و no-leak assertion ثبت شده است |

### Card C14 — Signed alert / anti-replay

| Field | Record |
|---|---|
| Report ID | `ACT-CHAOS-YYYYMMDD-C14` |
| Fault | alert signed/fresh، forged signature، stale timestamp و replay nonce به controller staging |
| Expected | فقط signed+fresh+allow-listed → Open؛ forged/stale/replay → 401/401/409 و state unchanged |
| Required evidence | signature verification outcome aggregate، nonce-store result، circuit before/after، controller audit و fake-provider count |
| PASS rule | receiver هرگز Close، rollout patch یا provider operation انجام نمی‌دهد؛ secret/body ثبت نشده است |

## 6. Decision rule

| تصمیم | شرط حداقلی |
|---|---|
| `PASS — model` | فقط pytest/deterministic evidence؛ وضعیت کنونی C03/C05/C08/C11/C13/C14 |
| `PASS — staging` | card کامل، UTC/version/metric/provider count/audit و reviewer sign-off staging |
| Limited Production | تمام P0ها `PASS — staging`، alert routing/rollback/kill drill و sign-off Engineering/SRE/Security/Privacy/Product |
| Broad Production | C09/C10/C15/C16 نیز `PASS — staging`، C16 rollback PASS، CAPA بسته و approval رسمی |

## References

[1] `ACTIVATION_CHAOS_REMAINING_GAPS_AND_PATCH_SPECIFICATION_FA.md`.

[2] `skills/activation-governance-chaos-rollout/SKILL.md` و `templates/scenario_evidence_card.md`.

[3] `skills/activation-governance-chaos-rollout/references/limited-rollout-thresholds.md`.

[4] Commit [`2f64f9b`](https://github.com/Ali-Marandi/DataSense/commit/2f64f9b) و testهای `enterprise_control_plane/tests/test_activation_governance_p0.py` و `test_activation_controller_auth.py`.
