# برنامهٔ Remediation و Test برای تبدیل ۱۰ سناریوی Chaos به PASS

## هدف و تعریف PASS

هدف این برنامه تبدیل **۳ سناریوی PARTIAL** و **۷ سناریوی NOT RUN** از register فعلی به `PASS — staging evidence` پیش از هر تصمیم دربارهٔ Broad Production است. این سند یک برنامهٔ اجرایی است؛ هیچ مورد را صرفاً به علت وجود design، unit model یا documentation پاس‌شده تلقی نمی‌کند.

> تعریف PASS: یک سناریو فقط زمانی PASS است که implementation مرتبط در commit مشخص موجود باشد، command/fixture در محیط non-production اجرا شود، زمان UTC و image/policy/migration version ثبت شود، result و metric snapshot نگهداری شوند، effect خارجی فقط به fake provider برسد، و reviewerهای لازم evidence را تأیید کنند.

## اصول غیرقابل‌مذاکره

| اصل | اثر در برنامه |
|---|---|
| Fail-closed | timeout، config نامعتبر، consent/recipient نامشخص و circuit state unknown همگی به `suppressed` می‌رسند. |
| No real external delivery | همهٔ testها از fake provider، synthetic tenant و fixture metadata-only استفاده می‌کنند. |
| No production chaos | harness فقط با `--environment test|staging --confirm-nonprod` اجرا می‌شود؛ production endpoint و customer data در allow-list نیستند. |
| Atomicity | state activation، audit، suppression و enqueue در یک transaction tenant-scoped نوشته می‌شوند. |
| Idempotency | effect خارجی با unique execution key محافظت می‌شود، نه فقط idempotency key Outbox. |
| Evidence discipline | PASS بدون artifact، reviewer و acceptance assertion ممنوع است. |

## موج‌بندی remediation

### Wave A — کنترل‌های لازم پیش از هر integration test

| Deliverable | مالک پیشنهادی | acceptance criterion |
|---|---|---|
| `ActivationPolicyService` و policy state store | Engineering + Security | default `UNKNOWN → suppress`؛ policy/consent/channel/recipient enumهای bounded. |
| `activation_cases`، `activation_suppressions` و `activation_trigger_executions` با RLS | Engineering | tenant isolation و unique `(org, case, trigger, version)` در integration test پاس شود. |
| `suppressed` به‌عنوان final Outbox state | Engineering | denial policy به retry/dead تبدیل نشود؛ transition test وجود داشته باشد. |
| fake provider و secure resolver test-double | Engineering/SRE | call counter و stable error injection داشته باشد؛ هیچ outbound network نداشته باشد. |
| circuit state store و controller interface | Platform/Security | Open/Manual Kill persist؛ Close نیازمند approval؛ alert input signed/replay-protected. |
| metricهای activation | Engineering/SRE | label bounded، zero raw data labels و scrape در staging. |

هیچ یک از سناریوهای C03 تا C16 بدون Wave A نباید PASS شود؛ اجرای دستی بدون این کنترل‌ها صرفاً discovery است.

### Wave B — تست‌های deterministic integration

C03، C05، C06، C07، C09، C10، C11، C13 و C14 ابتدا در integration environment با PostgreSQL/Redis test container یا equivalent isolated service اجرا شوند. Fake provider باید outbound network واقعی را به‌طور پیش‌فرض reject کند.

### Wave C — Staging chaos و release drill

C08، C15 و C16 و همچنین re-run سراسری سناریوهای Wave B در staging با Kubernetes، Alertmanager test receiver، ServiceMonitor و image digest immutable اجرا می‌شوند. این موج تنها با synthetic tenantهای allow-listed انجام می‌شود.

## نقشهٔ دقیق تبدیل سناریوها به PASS

| ID | وضعیت فعلی | remediation فنی | test/injection دقیق | PASS criterion و evidence | reviewer |
|---|---|---|---|---|---|
| **C03** | PARTIAL | circuit state persistent، token-bucket canary (`≤5/min`)، approval record با دو approver و close gate بسازید. | Open circuit؛ request Half-Open بدون approval؛ سپس approval معتبر؛ ۶ event synthetic در ۶۰s تزریق کنید؛ health false/true را تغییر دهید. | بدون approval = deny؛ event ششم suppress/rate-limited؛ Close فقط پس از health + approvals؛ audit/version trace موجود. | SRE + Security |
| **C05** | NOT RUN | policy/consent را در delivery time دوباره بخوانید؛ cancellation/revocation باید transactionally visible باشد. | event را enqueue/claim کنید؛ قبل از fake-provider call consent را revoke کنید؛ worker را ادامه دهید. | fake provider call count = 0؛ outcome `suppressed_consent_revoked`؛ retry ساخته نشود؛ audit row و counter موجود. | Privacy + Engineering |
| **C08** | NOT RUN | execution ledger unique، lease recovery و delivery handler idempotent را در PostgreSQL/Kubernetes تکمیل کنید. | worker پس از claim و قبل/بعد از execution ledger به‌طور کنترل‌شده kill شود؛ lease expire/recover شود. | حداکثر یک provider effect؛ stale lease recovery metric افزایش؛ event final state معتبر؛ worker restart evidence. | SRE + Engineering |
| **C09** | PARTIAL | fake provider با timeout/5xx، retry budget و policy re-check قبل از هر retry را به activation route متصل کنید. | first calls fake 503/timeout؛ circuit را پیش از retry باز کنید؛ سپس worker poll کنید. | retry bounded و stable code؛ وقتی Open است zero external retry؛ no duplicate effect؛ outcome/metric مطابق expectation. | Engineering + Security |
| **C10** | PARTIAL | error classification 4xx permanent، DLQ access control و ticketed/redrive authorization بسازید. | fake provider پاسخ 400 ثابت بدهد؛ تلاش کنید بدون ticket/admin role redrive کنید؛ سپس approved test ticket را بررسی کنید. | event `dead` با code bounded؛ redrive غیرمجاز rejected؛ raw payload نمایش داده نشود؛ audit کامل. | SRE + Security |
| **C11** | NOT RUN | event schema allow-list، payload validator و structured logging redaction را قبل از enqueue اعمال کنید. | fixture حاوی column name/path/value/email-like/unknown field را ارسال کنید؛ log capture و DB count بگیرید. | API reject ثابت؛ outbox insertion = 0؛ log/metric فاقد raw fixture؛ `payload_rejections_total` افزایش. | Security + Privacy |
| **C13** | NOT RUN | tenant-scoped kill switch با RLS و state lookup isolate بسازید. | دو synthetic tenant A/B، global circuit closed؛ فقط tenant A kill؛ برای هر دو external trigger ایجاد کنید. | A= suppressed kill، B= مطابق policy deliverable به fake provider؛ هیچ row/counter cross-tenant leakage ندارد. | Security + Engineering |
| **C14** | NOT RUN | Alertmanager receiver با HMAC یا mTLS، timestamp skew، nonce/replay store و allow-list alert/environment پیاده‌سازی کنید. | signed valid alert، signature غلط، alert قدیمی و nonce replay را ارسال کنید. | فقط valid/fresh alert state را Open کند؛ بقیه 401/403/409 ثابت و state unchanged؛ audit reason code ثبت. | Security + SRE |
| **C15** | NOT RUN | synthetic load generator، token bucket، queue priority/metric و kill switch drill را آماده کنید. | 10× baseline synthetic event با fake provider latency اجرا کنید؛ lag >900s را کنترل‌شده القا کنید. | controller Open؛ external post-open count=0؛ at-most-one effect؛ pending/dead/lease metrics و throughput graph ضبط؛ process پایدار. | SRE + Engineering |
| **C16** | NOT RUN | migration compatibility contract، rollout undo runbook و circuit state persistence را آماده کنید. | image digest جدید + compatible migration در staging deploy؛ circuit Open؛ `rollout undo` به digest قبلی؛ worker/API restart. | circuit state و suppression پابرجا؛ migration/data loss ندارد؛ schema compatibility check/rollback record و probes Green. | SRE + Engineering + Security |

## Test suite و ساختار artifact

### سطح ۱ — Unit / deterministic model

این سطح برای behaviorهای pure مانند state transition، rate cap، signature parsing و error classifier است. command پیشنهادی:

```bash
cd /workspace/datasense
python3 -m pytest -q enterprise_control_plane/tests/test_activation_*.py
python3 enterprise_control_plane/scripts/activation_circuit_breaker_simulation.py \
  --environment test --confirm-nonprod
```

این سطح به‌تنهایی PASS staging ایجاد نمی‌کند؛ فقط prerequisite است.

### سطح ۲ — Integration با dependencyهای مصنوعی

یک profile جداگانه باید PostgreSQL، Redis و fake provider داخلی را بالا بیاورد. `KUBECONFIG` واقعی، URL اینترنتی و secret تولید در این profile ممنوع‌اند.

```bash
# نمونهٔ contract، نه فرمان آمادهٔ production
DATASENSE_TEST_PROFILE=activation-integration \
DATASENSE_EXTERNAL_NETWORK=disabled \
python3 -m pytest -q enterprise_control_plane/tests/integration/test_activation_chaos_*.py
```

artifact هر test: JUnit، policy version، migration version، fake-provider call count، audit/suppression rows، Prometheus snapshot و redacted logs.

### سطح ۳ — Staging Kubernetes game day

قبل از اجرا، Release Owner باید `environment=staging`، synthetic tenant allow-list، fake provider DNS و change window را به‌صورت صریح تأیید کند. اسکریپت game day باید در absence `--confirm-nonprod` یا mismatch namespace فوراً exit non-zero کند.

```bash
# contract نمونه؛ فقط پس از پیاده‌سازی harness staging
./enterprise_control_plane/scripts/run_activation_chaos_staging.sh \
  --environment staging --scenario C08 --confirm-nonprod
```

هر scenario یک evidence card دارد و فقط پس از PASS card و reviewer به register منتقل می‌شود.

## Acceptance matrix برای تبدیل به PASS

| Gate | شرط عبور |
|---|---|
| Code | review، unit test و secret/payload scan Green است. |
| Integration | assertion فنی scenario در dependency مصنوعی PASS است. |
| Staging | همان assertion با deployment/metric واقعی staging PASS است. |
| Safety | fake-provider external effect دقیقاً مطابق expected count و بدون outbound network واقعی است. |
| Observability | dashboard، alert و correlation ID نشان می‌دهد fault مشاهده و containment شده است. |
| Governance | evidence card، owner، UTC، commit/digest، reviewer و CAPA ثبت شده‌اند. |

اگر هر Gate به FAIL برسد، scenario PASS نمی‌شود. اگر staging infrastructure آماده نیست، status باید `BLOCKED` ثبت شود، نه `PASS` یا `PARTIAL`.

## وابستگی‌ها و ترتیب اولویت

| اولویت | سناریوها | دلیل |
|---|---|---|
| P0 — قبل از Limited Production | C03, C05, C08, C11, C13, C14 | canary/approval، consent، crash safety، data minimization، tenant isolation و signed control plane، پایهٔ fail-closed هستند. |
| P1 — قبل از افزایش cohort | C09, C10, C15 | provider failure، DLQ governance و load behavior. |
| P2 — قبل از Broad Production | C16 | rollback/migration drill باید قبل از هر rollout گسترده PASS باشد. |

## CAPA register پیشنهادی

| CAPA | اقدام | سناریو | owner | evidence of completion |
|---|---|---|---|---|
| CAPA-A01 | persistent circuit + approval + rate cap | C03 | Platform | integration + staging trace |
| CAPA-A02 | delivery-time consent/policy re-check | C05, C09 | Engineering/Privacy | zero-call fake-provider test |
| CAPA-A03 | execution ledger و lease chaos | C08 | Engineering/SRE | pod-kill evidence |
| CAPA-A04 | schema/redaction gate | C11 | Security/Engineering | log/DB negative test |
| CAPA-A05 | tenant-scoped kill and RLS test | C13 | Security/Engineering | A/B isolation report |
| CAPA-A06 | signed/replay-safe alert receiver | C14 | SRE/Security | four-case signature test |
| CAPA-A07 | provider fault/DLQ contract | C09, C10 | Engineering/SRE | error-classification report |
| CAPA-A08 | synthetic load and rollback drill | C15, C16 | SRE/Engineering | game-day evidence cards |

## Production decision rule

**Limited Production** تنها پس از بسته‌شدن همهٔ P0ها، Green بودن baseline dashboards، ثبت alert routing و sign-off Security/SRE/Privacy/Engineering/Product قابل‌بررسی است. **Broad Production** تنها پس از PASS شدن C03 تا C16 در staging، صفر critical finding باز، و completion تمام CAPAها ممکن است.

## منابع داخلی

[1] `ACTIVATION_CHAOS_POST_INCIDENT_AND_VALIDATION_REPORT_TEMPLATE_FA.md`.

[2] `ACTIVATION_OUTBOX_CIRCUIT_BREAKER_AND_CHAOS_TEST_PLAN_FA.md`.

[3] `ACTIVATION_OBSERVABILITY_ALERTS_AND_INTERNAL_SIGNOFF_RUNBOOK_FA.md`.
