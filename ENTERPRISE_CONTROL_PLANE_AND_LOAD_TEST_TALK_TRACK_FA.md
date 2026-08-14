# متن گفتاری بخش معماری Control Plane و آزمون بارگذاری

## هدف بخش

این بخش برای اسلایدهای ۷ تا ۱۱ دک Enterprise v2.2.1 است. پیام اصلی آن این است که Trust Center desktop یک پایهٔ trusted analytics فراهم کرده، اما identity، authorization، notification و monitoring مرکزی باید به‌صورت server-side و با evidence پذیرش تحویل شوند. از ارائهٔ outbox/worker یا load test به‌عنوان قابلیت deploy‌شده در v2.2.1 خودداری کنید؛ این‌ها معماری، reference implementation و برنامهٔ پذیرش milestone بعدی هستند.

| اسلاید | مدت | پیام کلیدی |
|---:|---:|---|
| ۷ | ۱:۱۵ | Control Plane مرجع کنترل identity/policy/audit است، نه UI desktop. |
| ۸ | ۱:۰۰ | RBAC و tenant isolation باید server-side و deny-by-default باشند. |
| ۹ | ۱:۱۵ | SAML/PKCE/replay protection ورود سازمانی را ایمن می‌کند. |
| ۱۰ | ۱:۳۰ | outbox/worker و acceptance/load test مرحلهٔ hardening قابل‌اندازه‌گیری هستند. |
| ۱۱ | ۱:۱۵ | موفقیت با evidence و SLO سنجیده می‌شود، نه صرف ادعای معماری. |

## اسلاید ۷ — Enterprise Control Plane

**هدف بصری اسلاید:** نشان‌دادن مرز روشن میان desktop client و سرویس مرکزی.

**متن گفتاری پیشنهادی:**

«تا اینجا، DataSense Desktop شواهد کیفیت، schema و lineage را نزدیک به محل تحلیل نگه می‌دارد. برای سازمان چندکاربره، این کافی نیست. هویت، عضویت در سازمان، role، policy و audit باید در یک Control Plane مرکزی تصمیم‌گیری شوند. Desktop یک public client است؛ کاربر از browser سازمانی وارد می‌شود، اما تصمیم اینکه چه کسی به کدام dataset یا contract دسترسی دارد در server اجرا می‌شود. PostgreSQL مرجع دادهٔ پایدار و Redis محل state کوتاه‌عمر مانند transaction و replay protection است. نکتهٔ مهم این است که پنهان‌کردن یک دکمه در UI را امنیت نمی‌دانیم؛ authorization باید برای هر action و resource در backend enforce شود.»

**Talking points:**

مرجع فعلی شامل SAML، PKCE، JWT، RBAC و audit foundation است. سپس تأکید کنید که outbox/worker مانیتورینگ در برنامهٔ اجرای بعدی قرار دارد و هنوز سرویس production فعال نیست.

**گذار:** «این مرز معماری تنها وقتی ارزش دارد که permissionها با least privilege و isolation واقعی اعمال شوند.»

## اسلاید ۸ — RBAC و مجوزدهی قابل‌ممیزی

**هدف بصری اسلاید:** تبدیل نقش‌ها به policy قابل‌ردیابی، نه یک فهرست سمت client.

**متن گفتاری پیشنهادی:**

«مدل RBAC نقش‌های Owner، Admin، Data Steward، Analyst، Viewer و Auditor را به permissionهای ریزدانه تبدیل می‌کند. یک request معتبر همواره principal، organization و membership دارد. permission middleware ابتدا هویت را resolve می‌کند، سپس action و resource را در tenant صحیح بررسی می‌نماید. اگر resource متعلق به tenant دیگر باشد، پاسخ باید 404 یا deny امن باشد تا حتی وجود آن resource فاش نشود. تمام allow و denyهای مهم نیز به audit event تبدیل می‌شوند. به این ترتیب، یک Viewer نمی‌تواند policy را تغییر دهد و یک Analyst نمی‌تواند از مرز سازمان خود عبور کند.»

**Talking points:**

نقش‌های IdP source of truth مجوز نیستند؛ database membership/role سازمانی مرجع است. اگر دربارهٔ override Gate پرسیده شد، فقط permission محدود `contract.override_block` با ticket، TTL و audit باید آن را مجاز کند.

**گذار:** «پس از تعیین اینکه چه کسی مجاز است، باید مسیر صدور principal را نیز در برابر replay و سرقت credential ایمن کنیم.»

## اسلاید ۹ — SSO/SAML با امنیت پیش‌فرض

**هدف بصری اسلاید:** بیان جریان SP-initiated بدون ادعای استقرار production کامل.

**متن گفتاری پیشنهادی:**

«ورود از desktop با بازشدن browser سیستم آغاز می‌شود. Control Plane یک AuthnRequest امضاشده می‌سازد و request ID، RelayState و PKCE challenge را کوتاه‌مدت نگه می‌دارد. در ACS، امضا، issuer، audience، destination، recipient، زمان و InResponseTo اعتبارسنجی می‌شوند. assertion ID به‌صورت اتمی در replay cache ثبت می‌شود تا استفادهٔ مجدد رد شود. سپس به‌جای انتقال credential به desktop، authorization code کوتاه‌عمر صادر می‌شود و فقط با PKCE verifier درست قابل exchange است. این طراحی token، private key و raw assertion را از log و repository دور نگه می‌دارد.»

**Talking points:**

برای production، IdP staging، certificate rotation، KMS/HSM، secret manager و penetration test لازم است. از گفتن اینکه Entra/Okta integration live است خودداری کنید، مگر integration test سازمان اجرا شده باشد.

**گذار:** «اما identity به‌تنهایی کافی نیست؛ وقتی policy drift را block می‌کند، باید incident و notification را نیز قابل‌بازیابی تحویل دهیم.»

## اسلاید ۱۰ — مسیر تحویل پنج‌مرحله‌ای؛ افزودن Outbox/Worker

**هدف بصری اسلاید:** نشان‌دادن اینکه reliability و performance بعد از کدنویسی و قبل از production ارزیابی می‌شوند.

**متن گفتاری پیشنهادی:**

«مرحله‌های اول تا سوم Control Plane، RBAC و SAML را می‌سازند. در مرحلهٔ hardening، مانیتورینگ مرکزی Schema Drift را اضافه می‌کنیم. وقتی observation ناسازگار ثبت می‌شود، incident، audit event و outbox record در یک transaction ذخیره می‌شوند. worker جداگانه پیام را ارسال می‌کند؛ بنابراین failure شبکه مسیر API را block نمی‌کند و event commit‌شده گم نمی‌شود. اگر worker crash کند، lease recovery row را دوباره قابل‌پردازش می‌کند. اگر provider موقتاً خطا دهد، retry با backoff و jitter داریم؛ اگر failure دائمی یا retryهای زیاد رخ دهد، message به DLQ می‌رود تا با owner و evidence بررسی شود. چون delivery می‌تواند at-least-once باشد، destination با idempotency key از side effect تکراری جلوگیری می‌کند.»

**Talking points:**

تأکید کنید که این رفتار **هدف طراحی و برنامهٔ پذیرش** است، نه performance claim جاری. transaction atomic، `FOR UPDATE SKIP LOCKED` برای claim workerهای موازی، lease expiry، redrive کنترل‌شده و circuit breaker برای provider outage از معیارهای طراحی هستند.

**گذار:** «برای تبدیل این طرح به مجوز production، اجرای واقعی و اندازه‌گیری‌شدهٔ آزمون‌های پذیرش و بارگذاری لازم است.»

## اسلاید ۱۱ — معیارهای موفقیت؛ افزودن Acceptance و Load Testing

**هدف بصری اسلاید:** تعریف معیارهای قابل‌آزمون و پرهیز از KPI یا ظرفیت فرضی.

**متن گفتاری پیشنهادی:**

«موفقیت معماری با نمودار زیبا یا تعداد endpoint سنجیده نمی‌شود. برای پذیرش، باید ثابت کنیم request tenant دیگر denied و audit شده است؛ blocked observation به‌صورت اتمی incident و outbox می‌سازد؛ crash پس از claim به lease recovery می‌رسد؛ delivery تکراری side effect تکراری نمی‌سازد؛ و DLQ بدون silent loss قابل‌بررسی است. برای آزمون بارگذاری، Locust در محیط staging با payload metadata-only اجرا می‌شود و نه با داده یا credential واقعی مشتری. از smoke و baseline شروع می‌کنیم، سپس steady، burst، soak، fault injection و worker scale را اجرا می‌کنیم. p95/p99، error rate، queue depth، oldest pending age، retry/DLQ rate، database lock wait و provider failure همگی در یک Go/No-Go review بررسی می‌شوند.»

**Talking points:**

هم‌اکنون ۸۰ آزمون repository regression را تأیید می‌کنند؛ این عدد به‌معنای قبولی load test مرکزی نیست. SLOهای latency/throughput فقط پس از hardware و workload واقعی staging تصویب می‌شوند. هر result باید به artifact شامل Locust report، metrics snapshot، DB invariants، trace correlation و fake sink receipt متصل باشد.

**گذار به اسلاید ۱۲:** «با وجود این مرزهای روشن، درخواست تصمیم ما ساده است: baseline desktop را تثبیت کنیم و tenant پایلوت، IdP sandbox و ownerهای acceptance را همین حالا تعیین کنیم.»

## پاسخ‌های کوتاه برای پرسش‌های رایج

| پرسش | پاسخ پیشنهادی |
|---|---|
| آیا outbox/worker هم‌اکنون live است؟ | «خیر. طراحی، DDL، نمونه‌کد و برنامهٔ پذیرش آماده‌اند؛ استقرار بعد از staging و acceptance evidence انجام می‌شود.» |
| آیا ۸۰ test ظرفیت production را ثابت می‌کند؟ | «خیر. ۸۰ test regression و behavior را می‌سنجد؛ ظرفیت نیازمند load/soak/fault test با محیط و workload مصوب است.» |
| چرا delivery exactly-once نیست؟ | «provider acknowledgment و crash می‌تواند delivery را تکرار کند؛ به همین دلیل outbox at-least-once و destination idempotent طراحی می‌شود.» |
| چه چیزی مانع alert storm است؟ | «idempotency key، dedup incident، backoff+jitter، circuit breaker، rate limit و redrive کنترل‌شده.» |
| auto-blocking چه می‌کند؟ | «action حساس را متوقف می‌کند و evidence/reasons را نمایش می‌دهد؛ داده را حذف یا مخفیانه rule را تغییر نمی‌دهد.» |
