# Roadmap سی‌روزهٔ Onboarding و Triggerهای خودکار Customer Activation

## نتیجهٔ موردنظر

در پایان روز ۳۰، هر account واجد شرایط باید بتواند بدون خروج data خام از boundary محلی، نخستین workflow «گزارش مورداعتماد» را اجرا کند: import محلی، ایجاد یا review Contract، اجرای Quality Gate، تصمیم Schema Drift، evidence export و—در صورت مجازبودن policy—verification مستقل Signed Bundle. سیستم باید رفتارهای لازم را فقط با metadata محدود و pseudonymous اندازه‌گیری کند، accountهای در معرض activation failure را مشخص کند و triggerهای idempotent و rate-limited اجرا کند.

> این roadmap برای کاهش friction onboarding و یادگیری علل churn طراحی شده است. دستیابی به churn سالانهٔ ۱۲٪ یک فرضیهٔ cohort است، نه خروجی تضمین‌شدهٔ یک workflow یا trigger.

## تصمیم معماری پیش از شروع

| رویکرد | نحوهٔ اجرا | مزیت | trade-off | پیچیدگی / هزینه |
|---|---|---|---|---|
| **A. Trigger مرکزی مبتنی بر Control Plane و Outbox موجود** | رویدادها به transaction outbox افزوده می‌شوند؛ worker موجود با retry/DLQ، cueهای in-app و taskهای Customer Success را می‌رساند. | delivery قابل‌ردیابی، idempotency، metrics، tenant isolation و امکان رشد به notification channelهای تأییدشده. | نیازمند schema، policy consent، deployment worker و observability است. | متوسط؛ از اجزای موجود استفاده می‌کند. |
| **B. Trigger محلی در desktop app** | state activation فقط در `.dsproj` نگهداری می‌شود و cueها در Trust Center نمایش داده می‌شوند. | ساده‌تر، local-first کامل و بدون telemetry مرکزی. | cohort analytics، Customer Success follow-up و دید سازمانی ندارد. | کم؛ مناسب pilot بسیار حساس به data. |

هر دو رویکرد معتبرند. پیش از implementation، تیم باید با security owner تعیین کند که آیا metadata pseudonymous و automation مرکزی مجاز است یا pilot باید local-only بماند. roadmap فنی زیر، مسیر **A** را مشخص می‌کند؛ اگر مسیر B انتخاب شود، فقط مرحله‌های desktop و UX اجرا و مرحله‌های outbox/worker مرکزی حذف می‌شوند.

## اصول غیرقابل‌مذاکره

1. **Local-first data boundary:** event payload هرگز cell value، فایل، path محلی، value پارامتر rule، credential یا stack trace را حمل نمی‌کند.
2. **Consent و tenant control:** activation automation به‌صورت per-tenant opt-in است؛ tenant می‌تواند trigger، channel و retention را غیرفعال کند.
3. **At-least-once delivery، exactly-once effect:** Outbox ممکن است event را دوباره تحویل دهد؛ handler باید با `idempotency_key` و activation state، اثر یکتا ایجاد کند.
4. **Fail closed برای کانال خارجی:** بدون recipient verified، consent و policy مجاز، email/Slack/webhook ارسال نمی‌شود؛ فقط cue محلی یا task داخلی ثبت می‌شود.
5. **Rate limit و quiet period:** یک account حداکثر یک nudge خودکار در ۲۴ ساعت و یک escalation در هفت روز دریافت کند؛ user action باید هر countdown را reset کند.
6. **Human override و kill switch:** Customer Success و tenant admin باید بتوانند campaign را pause، state را reset و reason code را ثبت کنند.
7. **Observability بدون PII:** metricها aggregate و labelهای bounded دارند؛ event log به شناسهٔ pseudonymous و outcome محدود می‌شود.

## Activation state machine

| وضعیت | شرط ورود | شرط خروج | owner |
|---|---|---|---|
| `eligible` | tenant opt-in، owner نام‌دار، dataset و deliverable واقعی | `first_imported` یا `paused` | Customer Success / champion |
| `first_imported` | رویداد `dataset_imported` | `contract_ready` یا nudge-timeout | کاربر |
| `contract_ready` | `contract_created` یا review معتبر | `checks_run` | کاربر / reviewer |
| `checked` | `checks_run` با outcome ثبت‌شده | `evidence_exported` یا blocker triage | کاربر |
| `review_handoff` | `audit_exported` یا `signed_bundle_verified` | reviewer acknowledgement | reviewer/security owner |
| `activated` | یک Trusted Analysis Run و evidence قابل‌استفاده برای deliverable واقعی | usage cohort weekly | champion + sponsor |
| `at_risk` | timeout بدون رفتار بعدی یا blocker تکراری | `activated`، `paused` یا `disqualified` | Customer Success |
| `disqualified` | policy، data boundary یا no economic owner | close/re-discovery | founder / Sales |

`activated` به معنی renewal یا PMF نیست. این فقط نشان می‌دهد که اولین workflow کامل و قابل‌بررسی ایجاد شده است.

## قرارداد event و triggerها

### Envelope حداقلی

```json
{
  "event_id": "uuid",
  "event_type": "contract_created",
  "occurred_at": "2026-08-14T12:00:00Z",
  "organization_id": "pseudonymous-org-id",
  "actor_id": "pseudonymous-user-id",
  "activation_case_id": "uuid",
  "idempotency_key": "org:case:trigger:version",
  "outcome": "success"
}
```

payload نباید نام dataset، نام ستون، schema fingerprint، raw data، email یا متن خطا را حمل کند. اگر channel خارجی لازم است، mapping recipient در tenant-owned secure profile جداگانه نگهداری و در handler resolve می‌شود.

| رویداد | predicate | trigger | action مجاز | guardrail |
|---|---|---|---|---|
| `dataset_imported` | تا ۲۴ ساعت `contract_created` رخ نداده | `activation.create_contract.v1` | cue در Trust Center یا task CS | فقط یک‌بار در ۲۴ ساعت؛ reset با event بعدی |
| `contract_created` | تا ۲۴ ساعت `checks_run` رخ نداده | `activation.run_gate.v1` | cue برای اجرای Quality Gate | در صورت pause یا policy deny خاموش |
| `checks_run` | Gate fail یا blocked است | `activation.review_blocker.v1` | guide reason-code و task reviewer | error text وارد event نمی‌شود |
| `checks_run` | pass ولی تا ۷۲ ساعت export نیست | `activation.export_evidence.v1` | cue audit export | فقط برای workflow دارای deliverable |
| `audit_exported` | reviewer نام‌دار و consent دارد | `activation.reviewer_handoff.v1` | task برای reviewer / in-app notification | channel خارجی فقط پس از verified recipient |
| `signed_bundle_verified` | verification success | `activation.completed.v1` | activation success، suppression nudges، metric increment | evidence payload ذخیره نشود |
| هیچ eventی پس از activation | تا هفتهٔ سوم Trusted Run تکرار نشد | `activation.usage_risk.v1` | queue Customer Success | یک escalation در هفت روز |

## نقشهٔ تغییرات در codebase

| لایه | تغییر پیشنهادی | فایل/ماژول محتمل |
|---|---|---|
| Desktop event source | انتشار metadata-only event پس از import، Contract، Gate، export و verify | `core/data_manager.py`، `core/governance.py`، `core/evidence.py` |
| Control Plane API | endpoint batch idempotent برای activation event ingest، فقط برای tenant مجاز | `enterprise_control_plane/app/main.py` و service جدید `activation.py` |
| Persistence | activation case/state، trigger execution و suppression window با RLS | `enterprise_control_plane/schema.sql` و `repositories.py` |
| Outbox | event typeهای versioned مانند `activation.create_contract.v1` | `outbox.py` و writerهای repository |
| Worker handler | تصمیم deterministic، state transition اتمی، cue/task delivery | adapter جدید `activation_delivery.py` و `outbox_worker.py` |
| Metrics | activation funnel، suppressed triggers، delivery outcomes، state age | `metrics.py` و dashboard Grafana |
| UI | task pane Trust Center، دلیل trigger، dismiss/pause و privacy notice | `ui/trust_center_tab.py` |
| Tests | idempotency، duplicate delivery، quiet-period، tenant isolation، consent deny و redaction | `enterprise_control_plane/tests/` و `tests/` |

## برنامهٔ ۳۰ روزه

| روزها | هدف و deliverable | مالک پیشنهادی | معیار پذیرش |
|---:|---|---|---|
| ۱–۲ | workshop با Product، Security و Customer Success؛ انتخاب A یا B؛ تعریف data boundary و consent wording | Product owner | تصمیم معماری، DPA/consent review و owner matrix تایید شده باشد. |
| ۳–۴ | event taxonomy، activation state machine، reason-code taxonomy و idempotency convention | Backend + Security | نمونهٔ envelope بدون دادهٔ حساس و threat review سبک تایید شود. |
| ۵–۶ | schema migration برای activation case، trigger execution و RLS؛ feature flag tenant-level | Backend | migration rollback-tested و tenant isolation test پاس شود. |
| ۷–۹ | emission رویدادهای desktop و API ingest؛ event validation و redaction tests | Desktop + Backend | پنج event اصلی با duplicate replay بی‌اثر و payload redacted باشند. |
| ۱۰–۱۲ | activation decision handler و Outbox integration؛ retry، DLQ، quiet period و kill switch | Backend/SRE | هر trigger idempotent، rate-limited و observable باشد. |
| ۱۳–۱۵ | Trust Center task pane و مسیر ۳۰ دقیقه‌ای first trusted report | Product + Desktop | یک کاربر تست بدون راهنمای شفاهی workflow را تکمیل کند. |
| ۱۶–۱۸ | reviewer handoff، verified-recipient gating و policy deny path | Security + CS | بدون consent هیچ channel خارجی تحویل نگیرد؛ audit log reason code داشته باشد. |
| ۱۹–۲۱ | metrics، dashboard و risk queue؛ baseline funnel برای pilot | SRE + Product | funnel `eligible→activated` و age by state قابل مشاهده باشد. |
| ۲۲–۲۴ | اجرای pilot داخلی یا design partner؛ chaos test worker و duplicate/retry | QA + CS | no raw data in log، delivery retry/DLQ و recovery evidence ثبت شود. |
| ۲۵–۲۷ | remediation frictionهای top-three و بازآزمایی Time to First Trusted Report | Product | median زیر ۳۰ دقیقه در workflow واقعی pilot یا علت رد مستند باشد. |
| ۲۸–۳۰ | review امنیت/مالی، Go/Narrow/Pivot/Stop mini-memo و تصمیم rollout cohort بعدی | CEO/CTO/CISO | KPIها، blockerها، cost-to-serve و next decision ثبت شده باشند. |

## Definition of Done روز ۳۰

| حوزه | Definition of Done |
|---|---|
| محصول | اولین workflow مورداعتماد در Trust Center بدون خروج data خام و با مسیر recovery قابل‌فهم قابل‌اجرا است. |
| automation | triggerها idempotent، rate-limited، tenant-scoped، قابل pause و دارای retry/DLQ هستند. |
| امنیت | consent/policy gate، redaction، recipient verification، audit trail و kill switch آزمایش شده‌اند. |
| عملیات | dashboard funnel و alert برای DLQ، oldest pending outbox و activation state age فعال است. |
| تجاری | حداقل سه case qualified، یک baseline funnel و reason-codeهای churn-risk ثبت شده‌اند. |
| تصمیم | memo مشخص می‌کند که cohort بعدی scale شود، Narrow/Pivot شود یا توقف کند. |

## معماری تحویل و deployment

Triggerها rule-based و frequent هستند؛ بنابراین نباید به‌صورت اجرای دوره‌ای هوش‌مصنوعی یا polling گران اجرا شوند. اگر مسیر A انتخاب شود، delivery باید در همان Control Plane و worker موجود، با poll کوتاه worker و Outbox transactional فعلی باقی بماند. deployment می‌تواند در Kubernetes موجود انجام شود؛ worker تا زمانی که acceptance testها و policy consent پاس نشده‌اند در cohort محدود یا feature-flagged فعال می‌شود. برای pilot local-only، مسیر B نیاز به سرویس دائمی ندارد و cueها داخل desktop اجرا می‌شوند.

برای ارسال به email، Slack یا webhook خارجی، channel provider، webhook verification، recipient consent و secret management باید جداگانه انتخاب و اعتبارسنجی شود؛ تا پیش از آن، این roadmap فقط cue in-app و task داخلی را scope فعال تلقی می‌کند.

## منابع داخلی

[1] `RETENTION_ACCELERATION_PRICING_AND_ONBOARDING_PLAN_FA.md`.

[2] `GTM_PILOT_AND_MEASUREMENT_PLAN_FA.md`.

[3] `enterprise_control_plane/app/outbox.py`.
