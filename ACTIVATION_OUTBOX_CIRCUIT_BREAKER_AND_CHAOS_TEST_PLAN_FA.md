# پروتکل Circuit Breaker، Rollback و Chaos Test برای Activation Outbox

## هدف و اصل ایمنی

اگر در یک release پرحجم، سن Outbox pending از **۱۵ دقیقه** عبور کند، هدف نخست «رساندن سریع‌تر پیام» نیست؛ هدف، متوقف‌کردن هر اثر خارجیِ غیرضروری تا زمان اثبات سلامت policy، worker، database و channel است. Activation نباید کیفیت، امنیت یا delivery رویدادهای حیاتی مانند `quality_gate.blocked` را قربانی کند.

> اصل fail-closed: وضعیت circuit ناشناخته، policy خوانده‌نشده، consent نامعتبر، recipient تأییدنشده یا channel نامشخص همگی به معنی «عدم تحویل خارجی» هستند. automation فقط می‌تواند circuit را **باز** کند؛ بازگشایی delivery خارجی باید با evidence و تأیید انسانی انجام شود.

## ۱. Scope و تفکیک اولویت‌ها

Circuit breaker موضوع این سند تنها event typeهای `activation.*` را کنترل می‌کند. این breaker نباید eventهای quality gate، audit، security incident یا workflowهای قراردادی دیگر را delete یا بی‌اثر کند. برای جلوگیری از مخلوط‌شدن lag، Outbox باید در آینده metricهای age/depth به‌تفکیک `event_class` یا queue priority داشته باشد. تا قبل از آن، lag aggregate بالای ۱۵ دقیقه، external activation را احتیاطی pause می‌کند؛ زیرا سیستم هنوز نمی‌تواند ثابت کند کدام event class پشت صف مانده است.

| event class | رفتار در circuit Open | دلیل |
|---|---|---|
| `activation.external.*` | policy result = `suppressed_circuit_open`؛ بدون provider call | هیچ پیام خارجی قدیمی یا جدید ارسال نمی‌شود. |
| `activation.in_app.*` | پیش‌فرض pause؛ فقط اگر Product/Security آن را safe تعریف کرده باشند، cue محلی مجاز است | از افزایش pressure و پیام‌های گیج‌کننده جلوگیری می‌کند. |
| `quality_gate.*`, `audit.*` و security eventهای خارج از scope | تغییر نمی‌کنند؛ تحت runbook تخصصی خود باقی می‌مانند | blast radius activation محدود می‌ماند. |

## ۲. state machine Circuit Breaker

| state | تعریف | پذیرش trigger جدید | delivery خارجی | مسیر خروج |
|---|---|---|---|---|
| `CLOSED` | حالت عادی؛ lag و policy healthy | طبق policy | مجاز فقط با allow/consent/recipient verified | breach یا kill switch → `OPEN` |
| `OPEN` | fail-closed؛ activation external pause | trigger جدید audit/suppress می‌شود | ممنوع | health پایدار → `HALF_OPEN` فقط با approval |
| `HALF_OPEN` | canary کنترل‌شده | فقط allow-list tenant/case و سقف ثابت | حداکثر ۵ delivery آزمایشی در دقیقه | failure → `OPEN`؛ success evidence → `CLOSED` |
| `MANUAL_KILL` | kill switch Global یا Tenant فعال | همهٔ activationها suppressed | ممنوع | فقط owner مجاز پس از incident review |
| `UNKNOWN` | policy/circuit store در دسترس نیست یا signature controller نامعتبر است | default suppress | ممنوع | store/auth recovery + approval |

`OPEN` و `MANUAL_KILL` نباید به‌صورت خودکار به `CLOSED` برگردند. این انتخاب عمداً ریسک resume ناخواسته پس از یک transient recovery را حذف می‌کند.

## ۳. triggerهای خودکار و پروتکل ۱۵ دقیقه

### ۳.۱ شرط بازشدن خودکار

Circuit controller فقط یک webhook signed/mTLS از Alertmanager یا مسیر داخلی موردتأیید می‌پذیرد. Prometheus به‌تنهایی نباید permission تغییر state عملیاتی داشته باشد.

```promql
max(datasense_outbox_oldest_pending_age_seconds) > 900
```

شرط alert: `for: 2m`، `severity: critical` و `service: activation-outbox`. controller باید نام alert، environment، signature، freshness و allow-list cluster را اعتبارسنجی کند. هر mismatch به جای تغییر state، `automation_webhook_rejected` audit می‌شود.

### ۳.۲ اقدامات خودکار در ۰ تا ۲ دقیقهٔ پس از trigger

| زمان | اقدام خودکار | کنترل |
|---:|---|---|
| T+0 | `CLOSED → OPEN` با reason `outbox_lag_critical` و correlation ID | atomic update، audit event و metric. |
| T+0 | فعال‌سازی `activation_external_delivery_enabled=0` در policy store | worker policy re-check در هر delivery. |
| T+0 | suppress کردن triggerهای جدید `activation.external.*` با code پایدار | بدون Outbox external event جدید. |
| T+0 تا T+30s | worker claimهای activation external موجود را re-check می‌کند و final suppression ثبت می‌کند | provider call ممنوع؛ event قدیمی redrive نمی‌شود. |
| T+0 تا T+2m | Alert به SRE، Security، Product و Customer Success ارسال می‌شود | alert فقط داخلی است؛ مشتری خودکار مطلع نمی‌شود. |
| T+0 تا T+2m | freeze activation release/campaign version و ثبت deployment revision | از افزایش load یا action تکراری جلوگیری می‌کند. |

### ۳.۳ اقدامات انسانی در ۲ تا ۱۵ دقیقه

1. **SRE** worker health، DB connection pool، lock wait، throughput، provider timeout و lease recovery را بررسی می‌کند؛ هیچ payloadی در log باز نمی‌شود.
2. **Security** بررسی می‌کند که circuit واقعاً باز است، external-delivery count پس از trigger صفر شده و kill switch قابل‌استفاده است.
3. **Engineering** اختلاف release revision، migration و event volume را بررسی می‌کند. اگر lag با revision جدید هم‌بستگی دارد، rollout activation version undo می‌شود؛ اگر worker capacity محدود است، فقط طبق capacity runbook scale انجام می‌شود.
4. **Customer Success** پیام خارجی ارسال نمی‌کند. در صورت نیاز تجاری، فقط پس از triage و approval، status communication انسان‌محور منتشر می‌کند.

### ۳.۴ Rollback deployment

rollback فقط وقتی انجام می‌شود که یک revision یا config change با lag/denial/rejection هم‌بستگی داشته باشد؛ rollback «به‌خودی‌خود» جایگزین policy isolation نیست. ترتیب امن این است:

1. Circuit `OPEN` یا `MANUAL_KILL` را تایید کنید.
2. deployment/campaign activation جدید را freeze کنید.
3. نسخهٔ قبلی و migration compatibility را review کنید.
4. در **non-production**، rollout undo را با test cohort اجرا و metrics را مشاهده کنید.
5. در production، SRE و Security approval ثبت‌شده لازم است؛ سپس rollout revision قبلی با deployment controller اعمال می‌شود.
6. pending activation external eventهای دورهٔ incident را redrive نکنید. این eventها `suppressed_circuit_open` باقی می‌مانند و only a fresh, current-eligibility evaluation می‌تواند بعداً trigger جدید بسازد.

> عدم redrive پیام‌های قدیمی یک تصمیم privacy و تجربهٔ مشتری است: notification دیرهنگام ممکن است دیگر مناسب، مجاز یا مفید نباشد.

### ۳.۵ معیار Half-Open و Close

| شرط | مقدار پیشنهادی | owner |
|---|---:|---|
| oldest pending age | کمتر از ۳۰۰ ثانیه برای ۱۵ دقیقه | SRE |
| worker health و scrape | ۱۰۰٪ healthy | SRE |
| dead event trend | بدون رشد و triage تمام eventهای incident | Engineering/SRE |
| compliance violation | صفر از لحظهٔ Open | Security |
| policy / consent evaluation | pass در test suite و config version ثابت | Security/Privacy |
| canary external delivery | حداکثر ۵ در دقیقه، ۱۵ دقیقه، بدون retry/dead/denial غیرمنتظره | CS/SRE |
| sign-off برای `HALF_OPEN` | SRE + Security | Release owner |
| sign-off برای `CLOSED` | SRE + Security + Product | Release owner |

هر failure در Half-Open، حتی یک attempted effect بدون allow policy، بلافاصله `OPEN` را فعال و canary را متوقف می‌کند.

## ۴. Controller architecture و کنترل دسترسی

`ActivationCircuitController` باید یک component داخلی کوچک با access محدود باشد، نه یک webhook عمومی که مستقیم Kubernetes را patch کند.

| ورودی/خروجی | کنترل الزامی |
|---|---|
| Alertmanager webhook | mTLS یا HMAC rotateable، allow-list alert name/environment، replay/freshness check. |
| circuit state store | tenant/global scope، version، reason code، actor/correlation ID، append-only audit. |
| policy lookup در API/worker | timeout کوتاه و default `UNKNOWN → suppress`. |
| activation config | two-person approval برای close؛ write permission محدود به controller/authorized admin. |
| Kubernetes deployment rollback | جدا از controller؛ فقط SRE workflow با change record. |
| audit/metric | payload-less، error code bounded، immutable correlation. |

## ۵. chaos و simulation scenarios

تمام سناریوها ابتدا در unit/in-memory و staging اجرا می‌شوند. هیچ script این سند نباید production cluster، provider واقعی یا دادهٔ مشتری را تغییر دهد. harness باید با `--confirm-nonprod` و environment allow-list اجرا شود؛ نبود این flag یا environment نامطمئن باید exit non-zero داشته باشد.

| ID | fault injection | expected fail-closed behavior | acceptance evidence |
|---|---|---|---|
| C01 | lag synthetic بالای ۹۰۰s برای دو دقیقه | circuit به `OPEN`؛ external trigger جدید suppressed | state audit، metric، صفر provider call. |
| C02 | lag recovery بدون approval | state همچنان `OPEN` | عدم auto-resume. |
| C03 | approval Half-Open و canary healthy | فقط canary cap delivery؛ سپس Close با sign-off | canary trace و rate cap. |
| C04 | policy store timeout/unavailable | `UNKNOWN` و suppress؛ no retry delivery | zero external attempt و stable reason code. |
| C05 | consent revoked بعد از enqueue | worker re-check → suppress | no provider call after revocation. |
| C06 | recipient mapping missing | suppress `recipient_unverified` | audit/reason metric. |
| C07 | duplicate outbox delivery | یک execution effect؛ دوم `idempotent_skip` | unique execution assertion. |
| C08 | worker crash after claim | stale lease recover؛ re-check policy پیش از effect | at-most-one effect and recovery metric. |
| C09 | provider 5xx / timeout | bounded retry؛ اگر circuit Open شد no external retry | retry count و no policy bypass. |
| C10 | permanent 4xx | `dead` با stable code؛ redrive فقط با ticket | DLQ and audit. |
| C11 | invalid/raw-like payload | pre-enqueue reject؛ no queue/no log payload | payload rejection metric. |
| C12 | global kill switch | immediate suppress all activation routes | zero delivery after switch. |
| C13 | tenant kill switch | همان رفتار فقط tenant هدف، بدون cross-tenant effect | tenant isolation test. |
| C14 | invalid Alertmanager signature/replayed alert | controller reject؛ state تغییر نمی‌کند | rejection audit/metric. |
| C15 | flood (مثلاً 10× normal synthetic event) | rate limit، queue metric، no duplicate and no external after Open | throughput/lag graph + cap assertions. |
| C16 | deployment revision rollback | no schema/data loss، circuit state persists | migration/version evidence. |

## ۶. Definition of Done برای پیش‌تولید

- [ ] C01 تا C16 در CI یا staging با نتیجهٔ documented pass شوند.
- [ ] هیچ سناریو provider واقعی، customer data یا production endpoint را هدف نگیرد.
- [ ] failure policy/circuit lookup به `UNKNOWN → suppress` منتهی شود.
- [ ] circuit open، kill switch و policy revocation در آزمایش، zero external effect نشان دهند.
- [ ] duplicate/retry/lease scenario حداکثر یک effect داشته باشد.
- [ ] alert routing، on-call owner، rollback record و sign-offهای SRE/Security ثبت شوند.
- [ ] Open → Half-Open → Closed فقط مطابق approval matrix و evidence انجام شود.

## منابع داخلی

[1] `enterprise_control_plane/app/outbox.py` و `outbox_worker.py`.

[2] `enterprise_control_plane/app/repositories.py`.

[3] `ACTIVATION_OUTBOX_FAIL_CLOSED_PRODUCTION_ROLLOUT_GUIDE_FA.md`.

[4] `ACTIVATION_OBSERVABILITY_ALERTS_AND_INTERNAL_SIGNOFF_RUNBOOK_FA.md`.
