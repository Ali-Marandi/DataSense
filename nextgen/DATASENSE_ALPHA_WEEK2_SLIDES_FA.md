## Cover

# DataSense NextGen Alpha

### تحلیل محلیِ قابل‌اعتماد؛ خروجی تأییدشده؛ توسعهٔ هفتهٔ دوم

## Slide 1

# مسئله: تحلیل سریع، بدون ترک دستگاه

- تیم‌ها به insight سریع نیاز دارند، اما انتقال بی‌ضابطهٔ دادهٔ خام ریسک ایجاد می‌کند.
- DataSense Alpha مسیر **Explore → Validate → Deliver** را روی دستگاه کاربر نگه می‌دارد.
- هدف Alpha، اثبات یک تجربهٔ desktop قابل‌اعتماد پیش از گسترش محصول است.

## Slide 2

# Alpha بر سه ستون بنا شده است

- **Local-first:** CSV، preview، profile و تحلیل در فرایند محلی باقی می‌مانند.
- **Trust by design:** خروجی HTML فقط پس از کنترل کیفیت و همراه receipt امضاشده ساخته می‌شود.
- **Observable:** log چرخشی و error reference، عیب‌یابی را بدون افشای دادهٔ خام ممکن می‌کند.

## Slide 3

# گردش کار کاربر: از داده تا artifact

- **Explore:** بازکردن CSV/TSV/TXT، profile aggregate و preview محدود.
- **Prepare & Validate:** اجرای data contract، severityها و تشخیص findingهای مسدودکننده.
- **Deliver:** ایجاد HTML تأییدشده یا ثبت تصمیم Blocked با receipt metadata-only.

## Slide 4

# Data readiness قبل از تحلیل عمیق

- ماژول `DataReadinessInsightsModule` missingness، identifierهای احتمالی و outlierهای IQR را محلی بررسی می‌کند.
- امتیاز ۰ تا ۱۰۰ با آستانهٔ قابل‌تنظیم، فقط یک شاخص آمادگی است؛ تصمیم خودکار نیست.
- هشدارها تنها نام ستون و شمارش aggregate را نشان می‌دهند، نه valueهای حساس.

## Slide 5

# روز هشتم: قرارداد تحلیل را تثبیت کردیم

- ورودی فقط `pandas.DataFrame` با ستون‌های یکتا؛ خطاهای مرزی صریح و قابل‌آزمون هستند.
- تنظیمات immutable برای IQR، cardinality، حداقل مشاهده و readiness threshold.
- خروجی deterministic و عدم mutation ورودی، پایهٔ review و regression test را تقویت می‌کند.

## Slide 6

# روز نهم: diagnostics دقیق‌تر و مقاوم‌تر شد

- missingness اکنون نسبت‌محور است؛ اندازهٔ dataset در امتیاز اثر عادلانه دارد.
- مقدارهای `NaN`، `+∞` و `-∞` از outlier IQR جدا و به‌صورت aggregate ثبت می‌شوند.
- ستون‌های عددی یکتا به‌اشتباه identifier تلقی نمی‌شوند؛ فقط ستون‌های غیرعددی بررسی می‌شوند.

## Slide 7

# کیفیت در عمل: ۵۴ آزمون سبز

- مسیرهای healthy، empty، duplicate column، non-finite، threshold و immutability پوشش داده شدند.
- تست UI تضمین می‌کند readiness view مقدار نمونه یا دادهٔ خام را render نمی‌کند.
- تست کامل headless و بررسی نحوی، پیش از ارسال branch اجرا شده‌اند.

## Slide 8

# عیب‌یابی بدون data leak

- `datasense.jsonl` رویدادهای ساختاریافته و چرخشی را محلی نگه می‌دارد.
- `errors.jsonl` خطاها را با Error ID، component و متن redacted ثبت می‌کند.
- مسیرهای محلی و emailهای رایج در لایهٔ ثبت خطا redaction می‌شوند؛ ارسال telemetry پیش‌فرض غیرفعال است.

## Slide 9

# برنامهٔ هفتهٔ دوم: قابلیت، اعتماد، پذیرش

- **روزهای ۸ تا ۱۰:** readiness diagnostics، contract، unit test و UI binding.
- **روزهای ۱۱ و ۱۲:** structured logging، error monitoring و injection در composition root.
- **روزهای ۱۳ و ۱۴:** راهنمای کاربر، release rehearsal، smoke test و retrospective.

## Slide 10

# مسیر Alpha به بتا

- بهبود بعدی: UI پروژه‌های `.dsproj`، انتخاب contract و accessibility.
- پیش از production: code signing معتبر، installer hardening و policy پشتیبانی.
- معیار ادامه: feedback کاربران آزمایشی، کیفیت pipeline و نبود regression در جریان trusted export.

## Slide 11

# Alpha آمادهٔ ارزیابی کنترل‌شده است

### دریافت از Release، بررسی SHA-256، استفاده با دادهٔ غیرحساس و ثبت بازخورد
