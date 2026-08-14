# راهبرد کاهش ریسک برای milestoneهای Qualification امنیتی و مالی Enterprise

## هدف

هدف qualification سازمانی، عبور سریع‌تر از فروش نیست؛ حذف‌کردن accountهایی است که data boundary، security expectation، بودجه یا cost-to-serve آن‌ها با wedge فعلی DataSense سازگار نیست. هر milestone باید یک owner، artifact قابل‌بررسی، معیار عبور، معیار توقف و مسیر rollback داشته باشد.

> اصل حاکم: هیچ requirement امنیتی یا تجاری با عبارت «در roadmap است» پاسخ داده نمی‌شود. پاسخ معتبر فقط یکی از این سه حالت است: کنترل فعال و قابل‌آزمون؛ gap ثبت‌شده با acceptance criteria؛ یا عدم‌تناسب account با cohort فعلی.

## گیت صفر: Qualification پیش از راه‌اندازی

| پرسش gate | evidence لازم | Green | Red / تصمیم |
|---|---|---|---|
| مسئلهٔ واقعی وجود دارد؟ | incident، report/export و owner مشخص | quality/evidence واقعاً release را block می‌کند | بدون incident یا اثر؛ discovery مجدد یا Stop |
| data boundary سازگار است؟ | statement policy و نقش data owner | raw data محلی می‌ماند یا انتقال مجاز مشخص است | policy مبهم یا ممنوعیت حل‌نشده؛ pause تا clarification |
| sponsor و champion داریم؟ | نام، نقش و calendar commitment | champion کاربر و sponsor اقتصادی فعال‌اند | فقط علاقهٔ کاربر؛ pilot شروع نشود |
| مسیر خرید وجود دارد؟ | budget owner، procurement path و timeline | proposal path قابل‌ثبت | «بعداً بررسی می‌کنیم»؛ account در pipeline qualification بماند |
| scope قابل‌کنترل است؟ | pilot charter و acceptance criteria | یک workflow و یک deliverable واقعی | catalog/replacement کامل از روز اول؛ Narrow یا disqualify |

## milestoneهای qualification امنیتی

### S1 — Data boundary و privacy posture

**ریسک:** customer یا تیم فروش تصور کند bundle یا telemetry دادهٔ خام را حمل می‌کند، یا data classification قبل از pilot مبهم بماند.

| کنترل | evidence عبور | owner | معیار توقف / rollback |
|---|---|---|---|
| data-flow map از desktop تا Control Plane و verifier | diagram موردتأیید data owner، شامل مسیرهای ممنوع | Security architect + customer data owner | بدون approval: telemetry مرکزی خاموش و pilot local-only یا pause |
| payload allow-list | schema metadata-only و redaction test | Backend lead | هر payload حاوی raw value/path/secret: block release و incident review |
| consent و retention | tenant opt-in، retention window و DSR owner | Privacy owner | consent نامشخص: external delivery و activation trigger غیرفعال |
| classification review | دسته‌بندی metadata مانند column/rule/fingerprint | Customer security owner | metadata حساس بدون policy: local export تنها مسیر مجاز |

### S2 — Identity، tenant isolation و channel authorization

**ریسک:** trigger یا evidence به recipient اشتباه برسد، cross-tenant access ایجاد شود یا SSO به‌عنوان ادعای کامل بدون acceptance test فروخته شود.

| کنترل | evidence عبور | owner | معیار توقف / rollback |
|---|---|---|---|
| RBAC و tenant isolation tests | test result برای role و organization boundary | Engineering lead | failure isolation: pilot freeze و remediation پیش از access بیشتر |
| SSO/SAML discovery | IdP metadata، owner، test account و ACS acceptance criteria | Customer IAM owner + security lead | SSO blocker بدون owner: از custom build تعهد داده نشود |
| recipient verification | directory/mapping امن و consent channel | Customer Success + security | recipient unknown: فقط in-app cue، بدون email/Slack/webhook |
| service credential scope | least privilege، rotation owner و secret store | Platform/SRE | secret در log/repo: rotate، revoke و incident response |

### S3 — Evidence integrity و key lifecycle

**ریسک:** HMAC به‌اشتباه به‌عنوان non-repudiation عمومی معرفی شود یا key ownership مبهم باشد.

| کنترل | evidence عبور | owner | معیار توقف / rollback |
|---|---|---|---|
| key owner و key ID registry | owner، lifecycle و expected key ID ثبت‌شده | Customer security owner | key owner ندارد: Signed Bundle فقط demo/local، نه audit claim |
| independent verification | verifier output، tamper-fail evidence و test key | Reviewer + QA | verification failure: release block و key/path review |
| rotation/revocation runbook | incident procedure و re-signing policy | Security lead | compromised key: trust key ID متوقف، rotate و re-verify |
| asymmetric/KMS decision | threat model برای ممیز خارجی | Architecture council | بدون threat model: HMAC scope محدود به shared-secret pilot باقی می‌ماند |

### S4 — Operational resilience و auditability

**ریسک:** outbox trigger گم شود، delivery تکراری اثر مضاعف بسازد، یا DLQ بدون owner بماند.

| کنترل | evidence عبور | owner | معیار توقف / rollback |
|---|---|---|---|
| idempotency و atomic state transition | duplicate-delivery test و idempotency key | Backend lead | duplicate effect: trigger cohort pause تا fix |
| retry/DLQ/lease recovery | test evidence، dashboard و DLQ owner | SRE | DLQ age یا dead event بدون triage: external channel pause |
| audit trail | metadata-only audit record و actor/outcome | Compliance owner | log شامل sensitive payload: redact، retain مطابق policy و incident review |
| incident drill | tabletop برای key compromise و wrong-recipient | Security + CS | drill fail: pilot expansion متوقف |

## milestoneهای qualification مالی و تجاری

### F1 — Economic problem و sponsor

**ریسک:** کاربر product را دوست دارد، اما درد اقتصادی یا buyer وجود ندارد.

| کنترل | evidence عبور | owner | معیار توقف / rollback |
|---|---|---|---|
| value hypothesis | incident، زمان بازکاری، review delay یا risk صاحب‌دار | Champion + sponsor | value narrative عمومی: discovery ادامه، pilot پولی نه |
| sponsor confirmation | نقش، authority و decision date | Sales lead | sponsor absent: account به nurture، نه forecast pipeline |
| success metric | baseline و outcome مورد توافق | Product + customer | metric مبهم: pilot charter امضا نشود |

### F2 — Pricing و proposal qualification

**ریسک:** تخفیف برای پنهان‌کردن عدم‌تناسب استفاده شود یا price test بدون value/authority اجرا شود.

| کنترل | evidence عبور | owner | معیار توقف / rollback |
|---|---|---|---|
| package alignment | Professional، Team Evidence Pilot یا Enterprise package بر اساس workflow | Product + Sales | package مبهم: proposal صادر نشود |
| price test protocol | hypothesis، range، objection code و expiry | Sales Ops | discount بدون hypothesis: approval لازم یا stop |
| proposal review | buyer، procurement stage و timeline | Economic sponsor | proposal بدون owner/date: در pipeline weighted نشود |
| pilot credit terms | مبلغ pilot، credit rule، exit date و deliverable | Finance + Legal | credit یا refund policy مبهم: contract signing pause |

### F3 — Cost-to-serve و margin protection

**ریسک:** Enterprise onboarding سفارشی، security review یا support هزینه‌ای بسازد که ACV را بی‌اثر کند.

| کنترل | evidence عبور | owner | معیار توقف / rollback |
|---|---|---|---|
| onboarding SOW | milestone، ساعت/effort range، owner و dependency | Delivery lead | custom scope خارج از SOW: change request یا decline |
| security review cost log | زمان تیم، blocker و third-party dependency | CS + Security | هزینه بدون sponsor/proposal: engagement pause |
| support boundary | response channel، ساعات، named admins و escalation | Customer Success | support نامحدود: package revision پیش از ادامه |
| deal desk review | ACV، onboarding fee، discount، expected cost-to-serve | Finance + Sales | unit economics نامشخص: no-go یا Narrow |

### F4 — Conversion، renewal و collection hygiene

**ریسک:** pilot صرفاً به استفادهٔ کوتاه‌مدت تبدیل شود، owner تغییر کند یا invoice/contract process طولانی شود.

| کنترل | evidence عبور | owner | معیار توقف / rollback |
|---|---|---|---|
| mutual action plan | decision date، signer، security close و procurement steps | Sales lead | بدون decision date: pilot extension نیازمند approval |
| renewal signal | weekly Trusted Run، reviewer action و Contract reuse | CS | usage drop: churn-risk playbook، نه discount فوری |
| invoice readiness | legal entity، PO requirement، tax/payment owner | Finance Ops | اطلاعات ناقص: ARR در forecast ثبت نشود |
| cancellation taxonomy | pricing_value، workflow_fit، security_policy و… | Product + CS | reason unknown: close-lost analysis اجباری |

## Enterprise risk register

| ریسک | احتمال | اثر | کنترل اصلی | trigger اقدام | owner |
|---|---|---:|---|---|---|
| scope creep platform-wide | متوسط | زیاد | pilot charter و SOW | درخواست خارج از workflow | Product/Sales |
| data/telemetry policy conflict | متوسط | زیاد | local-only fallback و consent gate | policy deny | Security |
| key compromise یا signer ownership مبهم | کم تا متوسط | زیاد | key registry، rotation و drill | key owner missing/incident | Security |
| wrong recipient notification | کم | زیاد | verified recipient و fail-closed channel | mapping mismatch | CS/Security |
| duplicate trigger effect | متوسط | متوسط | idempotency/quiet period | replay test failure | Backend |
| budget mirage | متوسط | زیاد | named sponsor و proposal timeline | no owner/date | Sales |
| discount dependency | متوسط | متوسط | price test protocol و approval | off-menu discount request | Sales Ops |
| negative cost-to-serve | متوسط | زیاد | deal desk و milestone SOW | custom effort grows | Finance/Delivery |
| long security/procurement cycle | زیاد | متوسط | mutual action plan و stage ageing | date slips twice | Sales/Security |

## Decision rights و cadence

| تصمیم | تصمیم‌گیر نهایی | مشورت اجباری | cadence |
|---|---|---|---|
| اجازهٔ pilot | economic sponsor + DataSense Sales | Security, Product, CS | پیش از charter |
| فعال‌سازی trigger خارجی | tenant security owner | Privacy, CS, SRE | per tenant |
| تغییر price/discount | Sales leader / deal desk | Finance, Product | per proposal |
| custom security commitment | CTO/CISO | Legal, customer IAM | per requirement |
| Go/Narrow/Pivot/Stop | CEO/GM محصول | Sales, Product, Finance, Security | روز ۹۰ |

## نمره‌دهی Green / Yellow / Red

| حوزه | Green | Yellow | Red |
|---|---|---|---|
| امنیت | boundary، owner، test و runbook کامل | یک dependency یا evidence ناقص | policy/identity/key risk حل‌نشده |
| مالی | sponsor، proposal و cost-to-serve معلوم | buyer یا timeline در حال تکمیل | بدون budget path یا unit economics مبهم |
| محصول | workflow واقعی و activation قابل‌سنجش | friction یا reviewer gap | dataset/deliverable واقعی ندارد |
| عملیات | metrics، DLQ owner و kill switch فعال | یک alert/owner ناقص | delivery یا isolation failure |

Green در همهٔ حوزه‌ها شرط گسترش cohort است. Yellow فقط pilot محدود را اجازه می‌دهد و باید owner و تاریخ remediation داشته باشد. هر Red، expansion را متوقف می‌کند؛ bypass آن نیازمند تصمیم کتبی risk owner است.

## منابع داخلی

[1] `THIRTY_DAY_ONBOARDING_AND_ACTIVATION_TRIGGER_ROADMAP_FA.md`.

[2] `SIGNED_EVIDENCE_BUNDLE_GUIDE_FA.md`.

[3] `RETENTION_ACCELERATION_PRICING_AND_ONBOARDING_PLAN_FA.md`.

[4] `GTM_PILOT_AND_MEASUREMENT_PLAN_FA.md`.
