## Cover

# DataSense 2.2.1
### انتشار تجاری «Trusted Analytics» و مسیر دسترسی سازمانی

## Slide 1

# نسخهٔ قابل‌دانلود ویندوز، آمادهٔ استفاده است

- Release **v2.2.1** با build موفق Windows x64 منتشر شد.
- Installer، نسخهٔ Portable و executable مستقل در دسترس‌اند.
- 70 آزمون خودکار پیش از انتشار پاس شد.
- 2.2.1 جایگزین عملیاتی 2.2.0 و شامل اصلاح خط pipeline است.

## Slide 2

# Trust Center، تحلیل داده را قابل‌اعتماد می‌کند

- قرارداد داده، انتظارهای قابل‌تکرار را در کنار پروژه نگه می‌دارد.
- کیفیت داده پیش از تحلیل، export یا تصمیم‌گیری سنجیده می‌شود.
- شواهد JSON و timestamp UTC، خروجی را قابل‌ممیزی می‌کنند.
- تشخیص محلی دادهٔ حساس، گفت‌وگوی privacy را از ابتدای کار فعال می‌کند.

## Slide 3

# قرارداد داده: انتظارهای صریح، نتیجه‌های قابل‌توضیح

- Ruleهای موجود: null، یکتایی، بازه، allowlist، regex و freshness.
- هر rule نتیجهٔ pass/fail/error، مشاهده، انتظار و تعداد violation تولید می‌کند.
- نتیجه‌ها به Quality Report تبدیل و به JSON export می‌شوند.
- ruleهای پیشنهادی از schema داده آغاز سریع ایجاد می‌کنند.

## Slide 4

# امتیاز کیفیت، ریسک را وزن‌دهی می‌کند

- وزن severity: critical=4، high=3، medium=2 و low=1.
- **Score = 100 × وزن ruleهای pass ÷ وزن همهٔ ruleهای ارزیابی‌شده**.
- error در مخرج باقی می‌ماند؛ failure بحرانی مستقل از score، وضعیت را blocked می‌کند.
- نمونه: یک critical fail، یک high pass و یک low pass → **50.0% / Blocked**.

## Slide 5

# ارزش تجاری: از داشبورد به evidence قابل‌دفاع

- Gate کیفیت، ریسک دادهٔ نامعتبر در خروجی را آشکار می‌کند.
- قراردادها تحلیل را بین کاربر، پروژه و نسخهٔ داده تکرارپذیر می‌سازند.
- audit evidence به تیم داده، compliance و مشتری داخلی زبان مشترک می‌دهد.
- محصول برای تیم‌هایی طراحی شده که «چرا به این داده اعتماد کنیم؟» را می‌پرسند.

## Slide 6

# milestone بعدی: Enterprise Control Plane

- هویت و policy از فایل پروژه و دستگاه کاربر به یک مرز مرکزی منتقل می‌شود.
- Desktop تجربهٔ ورود و enforcement محلی را ارائه می‌کند.
- API مرکزی منبع تصمیم مجوز، audit، membership و license است.
- این طراحی، tenant isolation و policy واحد را ممکن می‌کند.

## Slide 7

# RBAC: مجوز، نه صرفاً پنهان‌کردن دکمه‌ها

- نقش‌ها مجموعه‌ای از permissionهای پایدار مانند `contract.run` و `audit.export` هستند.
- roleهای آغازین: Owner، Admin، Data Steward، Analyst، Viewer و Auditor.
- هر resource به سازمان تعلق دارد؛ همهٔ درخواست‌ها tenant boundary را بررسی می‌کنند.
- deny-by-default و ثبت اجازه/رد در audit، اجزای الزام‌آور هستند.

## Slide 8

# SSO/SAML: ورود مرکزی، کنترل محلی‌نشده

- Control Plane، SAML Service Provider مرکزی است؛ Desktop فقط browser login و PKCE را اجرا می‌کند.
- شروع با SP-initiated SSO؛ ACS اعتبار امضا، issuer، audience، recipient، زمان و `InResponseTo` را بررسی می‌کند.
- assertion تکراری با replay cache رد می‌شود؛ token کوتاه‌عمر و refresh rotation صادر می‌شود.
- metadata versioned، certificate rotation و audit برای هر اتصال سازمانی ضروری است.

## Slide 9

# نقشهٔ تحویل پنج‌مرحله‌ای، ریسک را محدود می‌کند

- **Control Plane:** سازمان، membership و audit پایه.
- **RBAC:** permission catalog، role editor و enforcement در API.
- **SAML SP:** metadata، ACS، Entra/Okta sandbox و آزمون‌های adversarial.
- **Desktop binding:** browser login، secure token storage و policy refresh.
- **Hardening:** rotation، SIEM export، SCIM و runbook رخداد.

## Slide 10

# معیار موفقیت: امنیت قابل‌سنجش، دادهٔ قابل‌اعتماد

- Viewer نمی‌تواند edit یا export کند؛ هر deny در audit ثبت می‌شود.
- assertion امضای نامعتبر، replay و audience mismatch رد می‌شوند.
- تغییر role حداکثر در 60 ثانیه در client اثر می‌گذارد.
- کیفیت، identity و evidence یک مسیر تجاری واحد می‌سازند.

## Slide 11

# تصمیم پیشنهادی

### DataSense 2.2.1 را به‌عنوان پایهٔ Trusted Analytics تثبیت کنید؛ سپس Control Plane، RBAC و SP-initiated SAML را به‌عنوان milestone سازمانی بعدی تحویل دهید.

### منابع: NIST RBAC، OASIS SAML 2.0 و OWASP SAML Security Cheat Sheet.
