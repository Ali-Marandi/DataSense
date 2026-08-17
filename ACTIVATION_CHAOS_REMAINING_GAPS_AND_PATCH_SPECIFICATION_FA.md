# مشخصات Patch برای شکاف‌های باقی‌ماندهٔ Activation Chaos

## تصحیح baseline و محدودهٔ review

register رسمی فعلی **۶ سناریوی partial یا failed ندارد**. وضعیت baseline صریح آن **۳ مورد PARTIAL** (`C03`, `C09`, `C10`)، **۷ مورد NOT RUN** (`C05`, `C08`, `C11`, `C13`, `C14`, `C15`, `C16`) و **۰ مورد FAIL مشاهده‌شده** است. بنابراین این سند به‌جای تولید مصنوعی «شش failure»، تمام ده شکاف واقعی را اولویت‌بندی می‌کند و برای شش مورد اول، patch scope کد-آماده ارائه می‌دهد.[1]

> وضعیت `NOT RUN` به معنای failure نیست؛ یعنی evidence اجرایی لازم وجود ندارد. تا زمان اجرای integration/staging و ثبت evidence card، هیچ‌یک PASS محسوب نمی‌شود.

## اولویت remediation

| اولویت | سناریو | وضعیت | چرا پیش از rollout لازم است |
|---|---|---|---|
| P0 | C03 | PARTIAL | بدون Half-Open cap و approval، recovery control قابل‌اعتماد نیست. |
| P0 | C05 | NOT RUN | consent باید بعد از enqueue و پیش از effect دوباره enforce شود. |
| P0 | C08 | NOT RUN | worker crash نباید duplicate effect بسازد. |
| P0 | C11 | NOT RUN | metadata boundary پیش از ورود به Outbox باید enforce شود. |
| P0 | C13 | NOT RUN | tenant kill و RLS باید از leakage جلوگیری کند. |
| P0 | C14 | NOT RUN | controller alert باید signed، fresh و replay-safe باشد. |
| P1 | C09 | PARTIAL | provider timeout/5xx نباید retry bypass بسازد. |
| P1 | C10 | PARTIAL | permanent failure و redrive باید governed باشند. |
| P1 | C15 | NOT RUN | lag/load behavior و circuit Open در staging باید مشاهده شود. |
| P2 | C16 | NOT RUN | migration/rollback drill شرط Broad Production است. |

## شش patch اولویت‌دار

### Patch A — C03: Persistent circuit، Half-Open cap و approval

**شکاف فعلی:** model transition دارد، اما rate limit، persistence، approval record و staging trace ندارد.

**فایل‌ها/ماژول‌های پیشنهادی:**

| محل | تغییر |
|---|---|
| `enterprise_control_plane/schema.sql` | جدول `activation_circuit_states` و `activation_circuit_approvals` با `tenant_id`, `scope`, `state`, `version`, `reason_code`, `opened_at`, `approved_by`, `approved_at`؛ unique scope و RLS اضافه شود. |
| `enterprise_control_plane/app/activation_circuit.py` | state machine transactional با `open()`, `request_half_open()`, `approve_half_open()`, `close()`؛ هر transition versioned/audited باشد. |
| `enterprise_control_plane/app/repositories.py` | compare-and-swap بر `version` و rate-window store برای `HALF_OPEN` اضافه شود. |
| `enterprise_control_plane/tests/integration/test_activation_circuit.py` | no-approval deny، cap `≤5/min`، race/CAS و persistence after restart را تست کند. |

**قرارداد رفتاری:** `OPEN` فقط با approval و health evidence وارد `HALF_OPEN` می‌شود؛ `HALF_OPEN` حداکثر پنج external attempt در هر ۶۰ ثانیه دارد؛ هر error غیرمنتظره به `OPEN` بازمی‌گردد؛ `CLOSED` فقط با Security+SRE approval و Product release approval ثبت می‌شود.

**سناریوی PASS:** ۶ fixture synthetic در ۶۰ ثانیه ثبت کنید. پنج تلاش اول طبق policy و fake provider مجازند؛ تلاش ششم `suppressed_rate_limited` می‌شود. Close بدون approval/health false رد می‌شود. پس از restart worker/controller، state و approvals باقی می‌مانند.

### Patch B — C05: consent revocation در لحظهٔ delivery

**شکاف فعلی:** design policy gate وجود دارد اما هیچ integration evidence بین claim و provider effect ندارد.

**فایل‌ها/ماژول‌های پیشنهادی:**

| محل | تغییر |
|---|---|
| `enterprise_control_plane/app/activation_policy.py` | `evaluate_delivery_eligibility()` با policy، consent، recipient، channel و circuit؛ timeout/unknown را `deny` کند. |
| `enterprise_control_plane/app/outbox_worker.py` | policy evaluation را بعد از claim و بلافاصله پیش از adapter call قرار دهد؛ denial را `suppressed` نهایی کند. |
| `enterprise_control_plane/app/repositories.py` | consent/policy read در transaction tenant-scoped و audit reason `consent_revoked` اضافه شود. |
| `enterprise_control_plane/tests/integration/test_activation_consent.py` | checkpoint پس از claim؛ revoke؛ سپس worker resume و fake provider count را assert کند. |

**قرارداد رفتاری:** revocation از retry، DLQ یا fallback delivery عبور نمی‌کند. `suppressed_consent_revoked` یک final state است و هیچ external retry تولید نمی‌کند.

**سناریوی PASS:** event synthetic claim شود؛ consent قبل از adapter call revoke شود؛ call count fake provider صفر، Outbox state `suppressed`, audit reason bounded و metric suppression افزایش یابد.

### Patch C — C08: execution ledger و crash-safe lease recovery

**شکاف فعلی:** Outbox عمومی lease دارد، اما activation execution ledger و pod-kill integration evidence ندارد.

**فایل‌ها/ماژول‌های پیشنهادی:**

| محل | تغییر |
|---|---|
| `enterprise_control_plane/schema.sql` | جدول `activation_trigger_executions` با unique `(tenant_id, execution_key)` و state `started|effect_recorded|suppressed|failed`. |
| `enterprise_control_plane/app/repositories.py` | `begin_activation_execution()` باید insert-on-conflict-safe باشد؛ effect outcome قبل از ack event ثبت شود. |
| `enterprise_control_plane/app/outbox_delivery.py` | adapter فقط پس از ledger grant فراخوانی شود؛ duplicate به `idempotent_skip` برسد. |
| `enterprise_control_plane/tests/integration/test_activation_lease_recovery.py` | crash در checkpoint قبل/بعد از ledger، lease expire و worker replacement را تست کند. |

**سناریوی PASS:** worker پس از claim و پیش از effect kill می‌شود؛ worker جدید lease را recover می‌کند؛ execution ledger یک row نهایی دارد؛ fake provider دقیقاً یک effect یا در حالت circuit Open صفر effect دارد. Database manual fix ممنوع است.

### Patch D — C11: schema firewall و redaction proof

**شکاف فعلی:** metadata-only contract مستند است، اما pre-enqueue validator و log assertion واقعی ندارد.

**فایل‌ها/ماژول‌های پیشنهادی:**

| محل | تغییر |
|---|---|
| `enterprise_control_plane/app/activation_payload.py` | dataclass/Pydantic-style bounded schema فقط با `event_type`, `case_id`, `trigger_version`, `policy_version`, `correlation_id`؛ unknown keys رد شوند. |
| `enterprise_control_plane/app/outbox.py` | activation event validation پیش از Outbox insert؛ failure reason bounded باشد. |
| `enterprise_control_plane/app/metrics.py` | `activation_payload_rejections_total{reason_code}` با enum محدود؛ بدون dynamic label. |
| `enterprise_control_plane/tests/test_activation_payload_redaction.py` | fixture با email-like value، path، dataset value، URL و unknown field؛ DB/log/metric assertion. |

**سناریوی PASS:** invalid fixture با HTTP/command result ثابت رد می‌شود؛ Outbox insertion صفر است؛ captured logs و `/metrics` فاقد raw token هستند؛ فقط reason code مثل `unknown_field` یا `sensitive_field` وجود دارد.

### Patch E — C13: tenant-scoped kill switch و RLS assertion

**شکاف فعلی:** global kill model شده، اما tenant-scoped behavior و isolation دیتابیس validate نشده است.

**فایل‌ها/ماژول‌های پیشنهادی:**

| محل | تغییر |
|---|---|
| `enterprise_control_plane/schema.sql` | `activation_kill_switches(tenant_id, scope, enabled, version, updated_by)`؛ unique tenant/scope و RLS role policy. |
| `enterprise_control_plane/app/repositories.py` | tenant context برای هر read/write؛ global/tenant precedence صریح. |
| `enterprise_control_plane/app/activation_policy.py` | `global kill OR tenant kill → suppress_kill_switch`؛ state unknown → suppress. |
| `enterprise_control_plane/tests/integration/test_activation_tenant_kill.py` | tenant A kill، tenant B healthy؛ cross-tenant select/update negative tests. |

**سناریوی PASS:** event A suppress می‌شود؛ event B فقط طبق policy خود به fake provider می‌رسد؛ credential/context A نمی‌تواند state یا execution B را read/update کند؛ metric label tenant ندارد.

### Patch F — C14: signed alert receiver و anti-replay

**شکاف فعلی:** alert/controller path فقط design است؛ هر untrusted input نباید اجازهٔ Open یا تغییر state داشته باشد.

**فایل‌ها/ماژول‌های پیشنهادی:**

| محل | تغییر |
|---|---|
| `enterprise_control_plane/app/activation_controller.py` | endpoint داخلی با HMAC یا mTLS، canonical body، timestamp window، nonce store و environment/alert allow-list. |
| `enterprise_control_plane/app/settings.py` | secret reference/key ID و allowed alert name/environment؛ secret هرگز log نشود. |
| `enterprise_control_plane/app/repositories.py` | nonce uniqueness با TTL و controller audit reason/code. |
| `enterprise_control_plane/tests/test_activation_controller_auth.py` | valid signature، invalid signature، stale timestamp و replay nonce؛ state assertions. |

**سناریوی PASS:** فقط alert صحیح، fresh و allow-listed circuit را Open می‌کند. invalid/stale/replay به 401/403/409 ثابت می‌رسد و state unchanged می‌ماند. هیچ webhook اجازهٔ Close، rollout patch یا provider action ندارد.

## چهار شکاف تکمیلی که نباید فراموش شوند

| سناریو | patch ضروری | معیار PASS |
|---|---|---|
| C09 | fake provider با error classifier؛ retry budget؛ policy/circuit re-check پیش از هر retry؛ Open پس از fault. | 503/timeout retry bounded؛ پس از Open fake provider call جدید صفر. |
| C10 | classification 4xx permanent؛ DLQ authorization و ticketed redrive؛ payload minimization. | state `dead` با code bounded؛ redrive غیرمجاز reject؛ no raw data. |
| C15 | synthetic generator guarded، fake-provider latency injection، metrics/alert receiver و event cap. | lag >900s برای window مشخص circuit را Open می‌کند؛ post-Open external effect صفر. |
| C16 | migration compatibility contract، pre/post rollback checks و persistent circuit state. | rollout undo state را حفظ می‌کند؛ schema/data loss ندارد؛ probes Green. |

## Dependency order و test gates

| Gate | سناریوها | محیط | وضعیت لازم |
|---|---|---|---|
| G1 | C03/C05/C11/C13/C14 | unit + integration | PASS integration با fake provider و isolated dependencies. |
| G2 | C08/C09/C10 | integration | PASS crash/retry/DLQ evidence. |
| G3 | C03/C05/C08/C09/C10/C11/C13/C14 | staging synthetic | PASS staging + reviewer card. |
| G4 | C15/C16 | staging game day | PASS staging + change/rollback artifacts. |

## CI/CD mapping

| Pull request | Protected staging promotion | Limited Production |
|---|---|---|
| skill/resource validator، pytest unit/integration، schema/manifest lint، dry-run guard | render immutable digest، server-side dry-run، synthetic game day، evidence artifact/sign-off | cohort allow-list، pager/live dashboard، manual approval، circuit/kill drill |

CI باید خطای code، resource integrity و non-production guard را block کند. CI نباید pod-kill، flood یا provider delivery واقعی اجرا کند؛ این‌ها فقط در protected staging با synthetic fixture و change approval مجازند.

## منابع داخلی

[1] `ACTIVATION_CHAOS_POST_INCIDENT_AND_VALIDATION_REPORT_TEMPLATE_FA.md`.

[2] `ACTIVATION_CHAOS_REMEDIATION_AND_PASS_CONVERSION_PLAN_FA.md`.

[3] `WAVE_A_SECURITY_VERIFICATION_AND_GREENLIGHT_CHECKLIST_FA.md`.
