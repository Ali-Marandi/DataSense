# ارائهٔ مدیریتی: Signed Evidence و راهبرد تجاری DataSense

## Cover

**DataSense: از تحلیل محلی تا evidence قابل‌دفاع**

راهبرد تجاری، Signed Evidence Bundle و تصمیم پایلوت ۹۰ روزه

## Slide 1

### تصمیم اصلی: پیش از توسعه، ارزش اقتصادی را اثبات کنیم

- مسئلهٔ هدف، «evidence قابل‌دفاع پیش از report/export» در workflow تحلیل جدولی حساس است.
- pilot برای اثبات یا رد willingness-to-pay طراحی شده است؛ نه صرفاً نمایش feature.
- North Star Metric، تعداد هفتگی Trusted Analysis Run است؛ فقط در کنار retention و outcome معنا دارد.

## Slide 2

### Signed Evidence، Trust Center را قابل‌ممیزی می‌کند

- Trust Center پس از اجرای Quality Check، یک JSON metadata-only قابل‌انتقال صادر می‌کند.
- HMAC-SHA256، digest canonical و key ID امکان verification مستقل و تشخیص tamper را فراهم می‌کنند.
- Bundle شامل contract خلاصه‌شده، quality gate، schema drift، history و lineage است؛ بدون cell value یا مسیر فایل محلی.

## Slide 3

### تضمین واقعی و مرز شفاف قابلیت

| آنچه اکنون کار می‌کند | آنچه عمداً ادعا نمی‌شود |
|---|---|
| Export امضاشده، CLI verification، tamper detection و عدم صدور raw value | رمزگذاری dataset، access control، KMS/HSM مدیریت‌شده یا امضای نامتقارن برای ممیز خارجی |
| Key file خارج از repository و key ID در bundle | lifecycle کامل KMS، registry policy و rotation خودکار |

> HMAC برای pilot محلی مناسب است؛ production گسترده نیازمند threat model و KMS یا امضای نامتقارن است.

## Slide 4

### پایلوت موفق با نصب موفق متفاوت است

- هر pilot باید dataset واقعی، deliverable واقعی، champion و sponsor اقتصادی داشته باشد.
- معیارهای یادگیری: کمتر از ۵ دقیقه تا trusted report در demo، بیش از ۵۰٪ reuse contract در هفته چهارم، و بیش از ۸۰٪ evidence completion.
- Signed Bundle تنها وقتی موفق است که reviewer مستقل آن را verify کند و policy مشتری اشتراک metadata را بپذیرد.

## Slide 5

### چهار خروجی تصمیم، سرمایه‌گذاری را منضبط می‌کنند

| نتیجه | evidence لازم | تصمیم بعدی |
|---|---|---|
| **Go** | حداقل دو pilot تکرارشونده، sponsor اقتصادی، blocker مشترک، proposal قابل‌قبول | verticalize message و Team/Enterprise motion |
| **Narrow** | ارزش فقط در یک workflow یا vertical دیده شود | product و template روی همان wedge متمرکز شود |
| **Pivot** | مسئله واقعی است، اما evidence-first خریداری نمی‌شود | positioning به integration/platform incumbent یا outcome عمودی تغییر کند |
| **Stop** | adoption و sponsor هر دو ضعیف‌اند | feature investment متوقف و discovery از صفر آغاز شود |

## Slide 6

### قیمت‌گذاری، فرضیهٔ پایلوت است نه قیمت فهرست

- Community Desktop: رایگان، با trust controlهای محلی و audit export پایه.
- Professional: ۳۹ دلار برای هر کاربر در ماه؛ بازهٔ آزمون ۲۹ تا ۴۹ دلار.
- Team/Business: ۵٬۰۰۰ دلار برای هر workspace در سال؛ بازهٔ آزمون ۳٬۰۰۰ تا ۹٬۰۰۰ دلار.
- Enterprise: ACV برنامه‌ریزی ۳۰٬۰۰۰ دلار به‌علاوهٔ onboarding ۷٬۵۰۰ دلار؛ فقط برای design partner.

## Slide 7

### سناریوی درآمد: دامنهٔ outcome بسیار وسیع است

- Downside 2030: 30,958.61 دلار درآمد؛ رشد و retention ناکافی.
- Base 2030: 573,511.10 دلار درآمد؛ رشد معتبر اما نیازمند efficiency.
- Upside 2030: 1,846,549.57 دلار درآمد؛ وابسته به growth، retention و enterprise win قوی.

> منبع: مدل برنامه‌ریزی پنج‌سالهٔ DataSense؛ این ارقام forecast، valuation یا guidance نیستند.

## Slide 8

### سودآوری فقط در Upside به نقطهٔ مثبت می‌رسد

- Downside 2030: EBITDA برنامه‌ریزی (442,149.89) دلار.
- Base 2030: EBITDA برنامه‌ریزی (141,921.84) دلار.
- Upside 2030: EBITDA برنامه‌ریزی 741,477.23 دلار.

> implication: پیش از scale sales، باید retention، price acceptance و cost-to-serve با data cohort واقعی اثبات شود.

## Slide 9

### اقدام ۹۰ روزه: evidence را به تصمیم تبدیل کنیم

- روز ۱ تا ۱۴: ۱۵ مصاحبه و پنج مسئلهٔ تکرارشونده با wording مشتری.
- روز ۱۵ تا ۶۰: سه pilot با dataset واقعی، Trust Center و Signed Bundle.
- روز ۶۱ تا ۹۰: security/SSO discovery، proposal test و تصمیم Go/Narrow/Pivot/Stop.

**درخواست تصمیم:** تایید ICP اولیه و اجازهٔ اجرای pilot evidence-first، پیش از ساخت قابلیت‌های platform-scale.

## Notes

تمام ارقام مالی از driverهای `DATASENSE_COMMERCIAL_PLANNING_MODEL.xlsx` بازسازی شده‌اند؛ رنگ‌ها و سناریوها برای نمایش مدیریت ریسک هستند و دادهٔ تاریخی یا پیش‌بینی خارجی محسوب نمی‌شوند. منبع قابلیت Signed Evidence، `SIGNED_EVIDENCE_BUNDLE_GUIDE_FA.md`؛ منبع معیارهای GTM، `GTM_PILOT_AND_MEASUREMENT_PLAN_FA.md` است.
