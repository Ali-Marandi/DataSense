# پیش‌نویس ایمیل خلاصهٔ اجرایی به هیئت‌مدیره

**موضوع:** تصمیم ۹۰ روزهٔ DataSense: اعتبارسنجی retention، ارزش evidence-first و مسیر Go/Narrow/Pivot/Stop

**گیرندگان:** اعضای هیئت‌مدیره

**رونوشت:** مدیرعامل، CTO، CISO، مدیر محصول و sponsor اقتصادی
**پیوست‌های پیشنهادی:** تحلیل حساسیت قیمت و churn، برنامهٔ retention/onboarding، دک ۱۰ اسلایدی و راهنمای مصاحبهٔ مشتری

اعضای محترم هیئت‌مدیره،

DataSense اکنون قابلیت **Signed Evidence Bundle** را در مسیر Trust Center دارد: یک artifact JSON metadata-only که با canonical digest، HMAC-SHA256 و key ID، integrity خروجی را قابل‌بررسی می‌کند. این قابلیت به‌طور طراحی‌شده دادهٔ خام، مقدار rule و مسیر فایل محلی را صادر نمی‌کند. در عین حال، آن را جایگزین KMS/HSM، رمزگذاری dataset، RBAC سراسری یا امضای نامتقارن برای ممیز خارجی معرفی نمی‌کنیم؛ این کنترل‌ها تنها پس از security review و توافق معماری مشتری وارد scope production می‌شوند.

تحلیل حساسیت مدل پنج‌ساله، اولویت عملیاتی مرحلهٔ بعد را روشن می‌کند. در سناریوی Base، درآمد برنامه‌ریزی‌شدهٔ ۲۰۳۰ **573,511.10 دلار** و EBITDA برنامه‌ریزی‌شده **(141,921.84) دلار** است. با ثابت نگه‌داشتن سایر driverها، بهبود churn سالانهٔ Professional از ۲۰٪ به ۱۲٪ در قیمت ۳۹ دلار، EBITDA ۲۰۳۰ را **36,422.69 دلار** بهتر می‌کند؛ افزایش ۲۰٪ قیمت Professional از ۳۹ به 46.80 دلار در churn پایه، EBITDA را **15,696.05 دلار** بهتر می‌کند. این نتیجه ثابت نمی‌کند که کاهش churn علت این بهبود است؛ اما نشان می‌دهد retention در محدودهٔ بررسی‌شده lever اقتصادی قوی‌تری از افزایش قیمت صرف است. هیچ ترکیب آزمایش‌شدهٔ قیمت و churn، EBITDA ۲۰۳۰ را به مثبت تبدیل نمی‌کند؛ بنابراین scale فروش بدون validation هم‌زمان retention، cost-to-serve و price acceptance توصیه نمی‌شود.

پیشنهاد مدیریت، اجرای یک برنامهٔ ۹۰ روزهٔ evidence-first است. در این برنامه، onboarding به مأموریت «اولین گزارش مورداعتماد» تبدیل می‌شود؛ هدف، تکمیل import محلی، Contract، Quality Gate، Schema Drift decision، evidence export و reviewer handoff در یک workflow واقعی است. در tierها، کاهش عمومی قیمت پیشنهاد نمی‌شود. Professional monthly با ۳۹ دلار به‌عنوان baseline باقی می‌ماند و آزمایش annual commitment فقط پس از activation انجام می‌شود. برای Team، یک Evidence Pilot اعتبارپذیر به قرارداد سالانه پیشنهاد می‌شود؛ برای Enterprise، onboarding milestone-based تنها پس از روشن‌شدن sponsor، security owner و procurement path آغاز می‌گردد.

نتیجهٔ برنامه در پایان روز ۹۰ با چهار معیار روشن ارزیابی می‌شود. **Go** تنها زمانی است که حداقل دو پایلوت usage تکرارشونده در هفتهٔ چهارم، sponsor اقتصادی، blocker مشترک و proposal قابل‌قبول داشته باشند. **Narrow** زمانی است که ارزش فقط در یک vertical یا workflow دیده شود. **Pivot** زمانی است که pain واقعی باشد اما evidence-first به‌عنوان budget line مستقل خریداری نشود. **Stop** زمانی است که adoption و sponsor اقتصادی هر دو ضعیف باشند. برای جلوگیری از برداشت نادرست از usage، معیارهای میان‌مرحله‌ای شامل Time to First Trusted Report کمتر از ۳۰ دقیقه در workflow واقعی، Contract reuse بیش از ۵۰٪ در هفتهٔ چهارم، Evidence completion بیش از ۸۰٪ و reviewer handoff تا روز ۱۴ هستند. این‌ها هدف‌های یادگیری‌اند، نه SLA یا تعهد فروش.

درخواست ما از هیئت‌مدیره سه تصمیم است: نخست، تأیید ICP اولیه و اجرای سه پایلوت واقعی با dataset و deliverable واقعی؛ دوم، تأیید اولویت retention و onboarding نسبت به توسعهٔ platform-scale تا زمان مشاهدهٔ usage، buyer و willingness-to-pay هم‌زمان؛ و سوم، تأیید چارچوب تصمیم Go/Narrow/Pivot/Stop به‌عنوان gate سرمایه‌گذاری بعدی. در پایان ۹۰ روز، تیم یک memo کوتاه با دادهٔ cohort، علت‌های رد، response proposal، blockerهای امنیتی و توصیهٔ تصمیم ارائه خواهد کرد.

با احترام،

**تیم DataSense**

## یادداشت افشا برای نسخهٔ ارسالی

ارقام مالی و قیمت‌ها در این ایمیل، فرضیات داخلی برنامه‌ریزی با تاریخ مبنا ۱۴ اوت ۲۰۲۶ هستند. این ارقام forecast، valuation، guidance سرمایه‌گذاری یا قیمت فهرست قطعی محسوب نمی‌شوند. تحلیل حساسیت نیز اثر conversion، چرخهٔ فروش و هزینهٔ واقعی onboarding را به‌طور کامل مدل نمی‌کند.

## منابع داخلی

[1] `PRICE_AND_CHURN_SENSITIVITY_ANALYSIS_FA.md`.

[2] `RETENTION_ACCELERATION_PRICING_AND_ONBOARDING_PLAN_FA.md`.

[3] `GTM_PILOT_AND_MEASUREMENT_PLAN_FA.md`.
