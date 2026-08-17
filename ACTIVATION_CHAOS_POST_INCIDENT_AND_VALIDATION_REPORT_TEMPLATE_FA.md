# قالب Post-Incident و Validation Report برای Chaos Engineering Activation Outbox

## ۱. کارکرد و قواعد گزارش

این سند برای دو موقعیت استفاده می‌شود: نخست، **Validation Report برنامه‌ریزی‌شده** پس از اجرای chaos/simulation در test یا staging؛ دوم، **Post-Incident Review** پس از یک breach واقعی مانند lag بحرانی، policy failure یا external effect غیرمجاز. هر گزارش باید واقعیت مشاهده‌شده را از design intent جدا کند. «سناریو تعریف شده»، «در harness شبیه‌سازی شده»، «در staging اجرا شده» و «در production اثبات شده» چهار سطح evidence متفاوت‌اند.

> قاعدهٔ گزارش‌دهی: status `PASS` فقط وقتی معتبر است که test command، محیط، زمان UTC، commit/artifact، نتیجه و reviewer ثبت شده باشند. نبود evidence یعنی `NOT RUN` یا `PENDING`، نه PASS.

## ۲. کنترل سند و خلاصهٔ اجرایی

| فیلد | مقدار قابل‌پرکردن |
|---|---|
| Report ID | `ACT-CHAOS-YYYYMMDD-###` |
| نوع گزارش | `Validation` / `Post-Incident` / `Combined` |
| محیط | `test` / `staging` / `production` |
| بازهٔ مشاهده | UTC start/end |
| Change / release revision | image digest، Git commit و config/policy version |
| Incident commander | نام و نقش |
| نویسنده و reviewer | نام/نقش/تاریخ |
| دامنه | activation event typeها، tenant cohort و channelهای مجاز |
| طبقه‌بندی داده | metadata-only؛ بدون raw payload در گزارش |
| وضعیت نهایی | `Green` / `Yellow` / `Red` |

### متن آمادهٔ Executive Summary

> در بازهٔ `<UTC range>`، ما `<N>` سناریوی chaos مربوط به Activation Outbox را در محیط `<environment>` ارزیابی کردیم. هدف، اثبات fail-closed بودن circuit، policy، consent، recipient verification و kill switch بود. از این سناریوها، `<pass>` مورد PASS، `<partial>` مورد PARTIAL، `<pending>` مورد NOT RUN/PENDING و `<fail>` مورد FAIL بودند. هیچ PASSی به production generalization تعمیم داده نشده است. تصمیم پیشنهادی: `<stay internal / limited cohort / pause / remediation>`.

## ۳. وضعیت پایه و محدوده

| موضوع | مقدار قبل از آزمون / incident | منبع evidence |
|---|---|---|
| Circuit state | `CLOSED` / `OPEN` / `MANUAL_KILL` / `UNKNOWN` | controller audit |
| Kill switch | global و tenant state | policy-store audit |
| Outbox oldest pending age | مقدار seconds و window | Prometheus snapshot |
| worker health | replicas ready / scrape status | Kubernetes + Prometheus |
| external delivery enabled | true/false با policy version | configuration audit |
| queue depth/status | pending / processing / dead | dashboard export |
| rollout/campaign version | version + change record | release record |
| customer impact | عدد aggregate، بدون tenant ID | CS incident summary |

**خارج از محدوده:** payload خام، محتوای message، recipient identity، dataset value، email، secret، URL provider و exception text نباید وارد گزارش شوند. در صورت نیاز forensic، مرجع محدودشدهٔ ticket/security vault درج شود، نه دادهٔ حساس.

## ۴. detection، timeline و containment

### ۴.۱ Detection record

| فیلد | مقدار |
|---|---|
| signal | نام alert / test assertion |
| expression یا test ID | مثال: `max(datasense_outbox_oldest_pending_age_seconds) > 900` |
| first observed UTC | `<timestamp>` |
| duration / `for` window | `<duration>` |
| correlation ID | `<stable identifier>` |
| automated controller decision | `OPEN` / rejected / none |
| human acknowledgement | owner و زمان |

### ۴.۲ Timeline (همه زمان‌ها UTC)

| زمان | رویداد مشاهده‌شده | اقدام خودکار | اقدام انسانی | evidence link/ID |
|---|---|---|---|---|
| T-15m | baseline | — | — | dashboard snapshot |
| T+0 | fault/alert | circuit state change یا rejection | on-call notified | audit/alert ID |
| T+30s | policy re-check | suppression / no provider call | SRE health review | metric snapshot |
| T+2m | containment verified | release freeze | Security review | change record |
| T+15m | diagnosis | — | rollback/scale decision | incident notes |
| T+30m | recovery evidence | — | Half-Open approval/reject | sign-off |
| T+45m | closure | — | post-check | dashboard export |

## ۵. Safety invariants و نتیجه

هر مورد زیر باید به‌صورت `PASS`، `FAIL`، `NOT RUN` یا `NOT APPLICABLE` ثبت شود.

| invariant | انتظار | status | evidence |
|---|---|---|---|
| no external effect under Open | وقتی circuit `OPEN` است provider call خارجی صفر است | `<status>` | counter + test/assertion |
| no auto-resume | recovery lag بدون approval state را `CLOSED` نمی‌کند | `<status>` | state audit |
| fail closed on unknown | timeout/unknown policy → suppression | `<status>` | test/result |
| consent gate at delivery | revocation بعد از enqueue delivery را suppress می‌کند | `<status>` | audit + provider call count |
| recipient gate | unresolved/invalid recipient → suppression | `<status>` | reason code counter |
| at-most-one effect | duplicate/retry/lease مسیر حداکثر یک effect خارجی دارد | `<status>` | execution unique assertion |
| kill switch dominance | Global/Tenant kill همهٔ اثرهای scope را متوقف می‌کند | `<status>` | state + zero delivery |
| no sensitive telemetry | raw payload/recipient در log/metric/report نیست | `<status>` | redaction test/review |

**Rule of interpretation:** هر `FAIL` در نخستین هفت invariant، وضعیت کلی را دست‌کم `Red` می‌کند. `NOT RUN` در سناریوی critical مانع production broad rollout است، حتی اگر harness دیگر PASS باشد.

## ۶. Scenario Validation Register — ۱۶ سناریو

### وضعیت baseline در commit `f7c4c22`

جدول زیر وضعیت صادقانهٔ evidence فعلی را نشان می‌دهد. harness in-memory فقط چهار test pytest و یک CLI simulation را اجرا می‌کند؛ به Kubernetes، Postgres، Alertmanager یا provider واقعی وصل نیست. بنابراین scenarioهای staging/integration به‌اشتباه PASS اعلام نشده‌اند.

| ID | سناریو | انتظار | evidence فعلی | status baseline | گام لازم برای validation کامل |
|---|---|---|---|---|---|
| C01 | synthetic lag >900s | `OPEN` و صفر external effect بعد از breach | unit test `test_lag_opens...` | **PASS — model** | staging: Alertmanager→controller signed path. |
| C02 | lag recovery بدون approval | Open باقی بماند | همان test؛ `close()` قبل از Half-Open رد می‌شود | **PASS — model** | staging: persistence across controller restart. |
| C03 | Half-Open canary healthy | cap و سپس Close با sign-off | transition model وجود دارد؛ rate cap ندارد | **PARTIAL** | canary limiter، sign-off API و staging trace. |
| C04 | policy store unavailable | `UNKNOWN → suppress` | unit test با state `UNKNOWN` | **PASS — model** | actual timeout/cache failure test. |
| C05 | consent revoked after enqueue | no provider call | طراحی مستند است | **NOT RUN** | integration test با policy change پس از claim. |
| C06 | recipient mapping missing | `recipient_unverified` suppress | unit test | **PASS — model** | secure resolver integration test. |
| C07 | duplicate delivery | exactly one external effect | unit test | **PASS — model** | database unique execution/replay test. |
| C08 | worker crash after claim | lease recovery + at-most-one effect | طراحی مستند است | **NOT RUN** | Kubernetes pod kill + PostgreSQL lease test. |
| C09 | provider 5xx/timeout | bounded retry؛ no bypass under Open | Outbox unit coverage قدیمی برای retry؛ activation integration ندارد | **PARTIAL** | fake provider + controller Open integration. |
| C10 | permanent 4xx | dead + audited redrive control | Outbox unit coverage قدیمی برای dead letter | **PARTIAL** | activation route/DLQ authorization test. |
| C11 | invalid/raw-like payload | pre-enqueue reject، no queue/log | طراحی مستند است | **NOT RUN** | schema/redaction test + log assertion. |
| C12 | global kill switch | suppress all activation routes | unit test | **PASS — model** | policy store/worker propagation test. |
| C13 | tenant kill switch | target tenant only | طراحی مستند است | **NOT RUN** | RLS/cross-tenant integration test. |
| C14 | forged/replayed controller alert | reject، state unchanged | طراحی مستند است | **NOT RUN** | signed webhook/replay test. |
| C15 | 10× synthetic flood | cap، no duplicate، Open suppress | طراحی مستند است | **NOT RUN** | staging load test with synthetic generator. |
| C16 | deployment rollback | state persists، no schema/data loss | طراحی مستند است | **NOT RUN** | staging rollout undo + migration compatibility test. |

### Per-Scenario Evidence Card

برای هر C01–C16 یک کارت مستقل پر کنید. در production، کارت باید به incident ticket و change record اشاره کند.

```markdown
## Scenario <C##> — <Title>

**هدف و risk مورد آزمایش:**

**محیط و safety boundary:** `test/staging`، synthetic fixture، no provider/customer data.

**Version evidence:** Git commit, image digest, policy version, migration version.

**Injection:** فرمان/fixture/پیکربندی دقیق و زمان UTC.

**Expected invariant:**

**Observed timeline:**

**Observed metrics:** oldest-pending age, policy decisions, suppressions, delivery outcome, worker health.

**External-effect proof:** provider mock call count = `<n>`؛ expected `<n>`.

**Result:** `PASS` / `PARTIAL` / `FAIL` / `NOT RUN`.

**Deviation and root-cause hypothesis:**

**Containment/rollback performed:**

**Corrective action:** owner, due date, verification test.

**Reviewer sign-off:** SRE / Security / Engineering / Product as applicable.
```

## ۷. Root-cause analysis بدون blame

در incident واقعی، علت را در پنج لایه بررسی کنید؛ نگویید «انسان خطا کرد» بدون آشکارکردن شرط سیستمی که خطا را ممکن کرده است.

| لایه | پرسش‌های هدایت‌کننده |
|---|---|
| Trigger | چه alert/test condition واقعاً رخ داد؟ false positive/negative داشت؟ |
| Policy | آیا consent، recipient، channel allow-list یا config version رفتار را تغییر داد؟ |
| Queue/worker | lag ناشی از volume، DB lock، worker crash، lease یا provider بود؟ |
| Delivery | retry/dead/suppression چگونه طبقه‌بندی شد؟ آیا effect ناخواسته رخ داد؟ |
| Governance | آیا owner، change record، sign-off یا kill-switch permission مبهم بود؟ |

## ۸. Impact و communications

| حوزه | معیار aggregate | نتیجه | owner |
|---|---|---|---|
| Security/privacy | attempted policy bypass، raw payload observation، recipient mismatch | `<result>` | Security/Privacy |
| Reliability | oldest age، dead ratio، retry exhaustion، worker unavailability | `<result>` | SRE |
| Product/activation | eligible→first trusted report، reviewer handoff، state age | `<result>` | Product/CS |
| Commercial | sponsor/pilot decision یا customer communication needed | `<result>` | Sales/CS |
| Financial | incident cost-to-serve، credit/contract impact (اگر applicable) | `<result>` | Finance |

هیچ اطلاع‌رسانی خارجی خودکار بر مبنای alert انجام نمی‌شود. Customer-facing communication باید پس از Security و CS triage، policy review و approval مناسب آماده شود.

## ۹. Corrective/Preventive Action Register

| ID | اقدام | نوع | priority | owner | due date | success metric | status |
|---|---|---|---|---|---|---|---|
| CAPA-001 | مثال: افزودن policy timeout integration test | Preventive | P0 | Engineering | `<date>` | C04 staging PASS | Open |
| CAPA-002 | مثال: rate cap واقعی Half-Open | Corrective | P0 | Platform | `<date>` | C03 PASS | Open |
| CAPA-003 | مثال: signed Alertmanager receiver | Preventive | P1 | SRE/Security | `<date>` | C14 PASS | Open |

## ۱۰. Final decision و sign-off

| نقش | تصمیم مجاز | نتیجه | نام/تاریخ | شرط باز |
|---|---|---|---|---|
| Incident commander / Release owner | Close / Continue / Pause | `<decision>` | `<name>` | `<condition>` |
| Security | Approve / Reject | `<decision>` | `<name>` | `<condition>` |
| Privacy | Approve / Reject / N/A | `<decision>` | `<name>` | `<condition>` |
| SRE | Approve / Reject | `<decision>` | `<name>` | `<condition>` |
| Engineering | Approve / Reject | `<decision>` | `<name>` | `<condition>` |
| Product | Approve / Reject | `<decision>` | `<name>` | `<condition>` |
| Customer Success | Approve / Reject / N/A | `<decision>` | `<name>` | `<condition>` |

### Decision rule

| وضعیت | مجاز است؟ |
|---|---|
| هر invariant critical FAIL | production rollout متوقف؛ circuit Open یا Manual Kill مطابق severity. |
| هر scenario critical NOT RUN | broad production مجاز نیست؛ فقط internal/staging یا pilot محدود با risk acceptance مکتوب. |
| PARTIAL بدون CAPA owner/date | Yellow هم مجاز نیست. |
| PASSهای model بدون staging evidence | صرفاً evidence اولیه؛ معادل production readiness نیست. |
| همهٔ critical scenarios staging PASS، sign-off کامل، Red باز صفر | limited production طبق cohort policy قابل‌بررسی است. |

## منابع داخلی

[1] `ACTIVATION_OUTBOX_CIRCUIT_BREAKER_AND_CHAOS_TEST_PLAN_FA.md`.

[2] `enterprise_control_plane/scripts/activation_circuit_breaker_simulation.py`.

[3] `enterprise_control_plane/tests/test_activation_circuit_breaker_simulation.py`.

[4] `ACTIVATION_OBSERVABILITY_ALERTS_AND_INTERNAL_SIGNOFF_RUNBOOK_FA.md`.
