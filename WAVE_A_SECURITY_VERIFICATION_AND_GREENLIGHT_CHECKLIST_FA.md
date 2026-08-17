# Checklist امنیتی Wave A و معیار Greenlight

## تصمیم مورد درخواست

این checklist برای تصمیم Security دربارهٔ فعال‌سازی **Wave A activation integration** در محیط test/staging و cohort محدود طراحی شده است. این تصمیم مجوز Broad Production، ارسال پیام به مشتری، فعال‌سازی provider واقعی یا انجام chaos در production نیست.

> Security فقط در صورت مشاهدهٔ evidence قابل‌تکرار و بدون finding بحرانی می‌تواند `APPROVE` یا `APPROVE WITH CONDITIONS` ثبت کند. نبود evidence، تصمیم `REJECT` است؛ نه موافقت مشروط بدون owner و تاریخ.

## ۱. بستهٔ review که Release Owner باید تحویل دهد

| مورد | evidence الزامی | وضعیت |
|---|---|---|
| Version manifest | Git commit، image digest، policy version، migration version و environment | ☐ |
| Scope manifest | event typeهای مجاز، channelها، cohort synthetic/allow-listed و fake provider | ☐ |
| Architecture | sequence diagram از trigger تا suppression/delivery و state diagram circuit | ☐ |
| Data map | فیلدهای metadata-only، retention owner و ممنوعیت raw payload/recipient/secret | ☐ |
| Test index | link/ID تست‌های unit، integration و staging مورد نظر | ☐ |
| Metrics map | نام metricها، label enumها، alert route و redaction rule | ☐ |
| Change/rollback record | approved rollback target، kill-switch owner، change window | ☐ |
| Open-risk register | Yellow/Redهای باز با owner، due date و retest scenario | ☐ |

Security نباید review را آغاز کند اگر version manifest یا scope manifest ناقص است؛ این دو مورد حداقل لازم برای traceability هستند.

## ۲. دروازهٔ fail-closed و policy delivery-time

| کنترل | روش verification | PASS criterion | blocker اگر شکست خورد |
|---|---|---|---|
| Policy missing | policy store را برای fixture مصنوعی unavailable کنید. | final outcome `suppressed_unknown` یا معادل bounded؛ fake-provider calls = 0. | هر retry یا delivery خارجی. |
| Consent revoked after enqueue | event را enqueue/claim کنید، سپس consent را revoke و worker را ادامه دهید. | `suppressed_consent_revoked`، call count = 0، audit/counter ثبت. | reliance فقط به enqueue-time approval. |
| Recipient unresolved | resolver را برای fixture synthetic خالی/invalid کنید. | `recipient_unverified`، call count = 0. | fallback recipient یا channel default. |
| Channel unapproved | channel/template خارج allow-list inject کنید. | pre-delivery suppress؛ no provider call. | provider call یا suppression reason بدون taxonomy. |
| Circuit unknown/open | circuit store timeout و سپس state Open را inject کنید. | `UNKNOWN → suppress` و `OPEN → suppress`. | delivery هنگام state نامشخص. |

**Evidence لازم:** command/fixture، UTC time، policy/config version، fake-provider call count، audit ID، metric snapshot و reviewer نام‌دار. هیچ screenshot فاقد version و زمان، evidence کافی نیست.

## ۳. transaction، tenant isolation و idempotency

| کنترل | روش verification | PASS criterion | owner اصلی |
|---|---|---|---|
| Atomic write | trigger را زیر fault قبل/بعد از enqueue اجرا کنید. | state، audit، suppression و enqueue یا همگی commit یا همگی rollback شوند. | Engineering |
| Tenant RLS | دو tenant synthetic A/B ایجاد کنید؛ با credential A تلاش read/write/update state B کنید. | 0 row / forbidden؛ metric و audit بدون cross-tenant label. | Engineering + Security |
| Tenant kill switch | فقط A را kill کنید و triggerهای A/B را اجرا کنید. | A suppress؛ B فقط طبق policy خود؛ data leakage صفر. | Engineering + Security |
| Execution idempotency | duplicate، retry و replay یک execution key را اجرا کنید. | حداکثر یک fake-provider effect؛ تلاش بعدی `idempotent_skip`. | Engineering |
| Lease recovery | worker بعد از claim و قبل/بعد از ledger به‌صورت کنترل‌شده متوقف شود. | stale lease recover؛ حداکثر یک effect و audit کامل. | SRE + Engineering |

**Greenlight rule:** RLS و unique execution key باید به‌صورت schema/constraint و integration test ثابت شوند. اعتماد به application code بدون database boundary کافی نیست.

## ۴. کنترل circuit، kill switch و authority

| کنترل | verification | PASS criterion |
|---|---|---|
| Open authority | alert/controller input فاقد signature، timestamp قدیمی، nonce replay و environment mismatch را ارسال کنید. | state تغییر نمی‌کند؛ bounded rejection audit ثبت می‌شود. |
| Close authority | تلاش Close از `OPEN` بدون approval/health و از `UNKNOWN` را اجرا کنید. | close رد می‌شود؛ audit reason ثبت می‌شود. |
| Half-Open cap | بیش از ۵ event/minute به canary synthetic ارسال کنید. | سقف enforce؛ event اضافی suppress/rate-limit؛ full traffic restore رخ نمی‌دهد. |
| Global kill | kill را فعال و همهٔ routeهای activation را invoke کنید. | zero external effect؛ state/audit قابل‌ردیابی. |
| Kill persistence | controller/worker restart را با kill فعال انجام دهید. | restart نمی‌تواند kill یا Open را به Closed برگرداند. |
| Rollback separation | request rollback را به controller input ارسال کنید. | controller مستقیماً deployment patch نمی‌کند؛ rollback فقط SRE workflow/change record دارد. |

**بلاک‌کننده:** webhook عمومی بدون HMAC/mTLS، replay protection یا environment allow-list؛ همچنین هر close خودکار یا actor بدون authorization.

## ۵. data minimization، logging و telemetry

| کنترل | روش verification | PASS criterion |
|---|---|---|
| Schema allow-list | fixture شامل email-like value، dataset value، column/path، URL و field ناشناخته بفرستید. | pre-enqueue reject؛ Outbox rows = 0. |
| Log redaction | log capture برای rejection، provider failure و worker crash اجرا کنید. | raw payload، recipient، secret، URL و exception body وجود ندارد. |
| Metric labels | scrape `/metrics` و dashboard query را review کنید. | فقط enumهای bounded؛ بدون org/account/user/email/request/dataset/provider URL. |
| Audit content | audit export را review کنید. | metadata-only، correlation ID و stable reason code؛ بدون sensitive payload. |
| DLQ access | role غیرمجاز برای DLQ/redrive تلاش کند. | access denied؛ payload در UI/log incident آشکار نمی‌شود. |

Security باید sampling را از artifact واقعی اجرای test بگیرد، نه فقط code inspection. اگر redaction test وجود ندارد، Wave A Green نیست.

## ۶. secret، dependency و platform boundary

| کنترل | evidence | PASS criterion |
|---|---|---|
| Secret delivery | manifest/secret reference review | secret در source، ConfigMap، metric یا log نیست؛ least privilege mount. |
| Service account RBAC | Kubernetes RBAC review | worker/controller فقط resourceهای ضروری را دارد؛ no cluster-admin. |
| Network policy | ingress/egress review | fake provider/staging endpoints explicitly allow-listed؛ outbound default deny در صورت امکان. |
| Dependency posture | lockfile/SBOM or scan result | critical known finding بدون mitigation/owner وجود ندارد. |
| Database identity | role/RLS verification | tenant-scoped access، migration role و worker role تفکیک شده‌اند. |

## ۷. اجرای sign-off security drill

یک Security reviewer و یک Engineering/SRE observer باید حداقل تمرین زیر را در staging یا integration ایزوله ثبت کنند:

1. C05: revocation بعد از enqueue؛ fake provider call = 0.
2. C11: raw-like payload؛ Outbox row = 0 و logs redacted.
3. C13: tenant kill switch؛ isolation A/B.
4. C14: forged/replayed signed alert؛ state unchanged.
5. C03: Half-Open بدون approval و بیشتر از cap؛ no automatic Close.
6. C08: worker/lease scenario؛ at-most-one external effect.

هر drill باید یک evidence card مستقل داشته باشد. اگر یک مورد هنوز پیاده‌سازی نشده است، تصمیم باید `REJECT` یا `APPROVE WITH CONDITIONS` با cohort scope صفر برای آن channel باشد؛ آن مورد PASS نیست.

## ۸. معیار تصمیم و امضا

| تصمیم | معیار |
|---|---|
| `APPROVE` | همهٔ کنترل‌های بخش‌های ۲ تا ۶ PASS؛ P0 evidence موجود؛ finding critical باز صفر؛ runbook/kill switch drill معتبر. |
| `APPROVE WITH CONDITIONS` | هیچ critical finding باز وجود ندارد؛ conditions محدود، non-security-bypass، دارای owner/date/retest هستند؛ cohort و channel به‌صورت صریح محدود شده‌اند. |
| `REJECT` | هر policy bypass، RLS failure، sensitive telemetry، external effect در Open/Unknown، missing signed controller input، missing evidence یا kill-switch failure. |

### فرم نهایی Security

```markdown
Decision: APPROVE | APPROVE WITH CONDITIONS | REJECT
Environment and cohort approved: <test/staging/allow-listed cohort>
Commit/image/policy/migration reviewed: <values>
Evidence cards reviewed: <IDs>
Critical findings: <none / IDs>
Conditions (if any): <owner, date, retest>
Allowed external channel scope: <none / constrained scope>
Reviewer: <name, role>
UTC timestamp: <time>
```

**امضای شفاهی، reaction در chat، یا تأیید بدون version manifest معتبر نیست.**

## منابع داخلی

[1] `ACTIVATION_CHAOS_REMEDIATION_AND_PASS_CONVERSION_PLAN_FA.md`.

[2] `ACTIVATION_LIMITED_PRODUCTION_ONCALL_RUNBOOK_AND_ALERT_THRESHOLDS_FA.md`.

[3] `ACTIVATION_OUTBOX_CIRCUIT_BREAKER_AND_CHAOS_TEST_PLAN_FA.md`.
