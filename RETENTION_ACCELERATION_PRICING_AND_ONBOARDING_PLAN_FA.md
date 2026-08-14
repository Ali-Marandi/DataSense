# برنامهٔ شتاب‌دهی Retention: قیمت‌گذاری و Onboarding برای هدف churn از ۲۰٪ به ۱۲٪

## تصمیم پایه

مدل برنامه‌ریزی نشان می‌دهد که در سناریوی Base، کاهش churn سالانهٔ Professional از ۲۰٪ به ۱۲٪، با ثابت نگه‌داشتن سایر driverها، اثر EBITDA ۲۰۳۰ بیشتری از افزایش ۲۰٪ قیمت Professional دارد: **36,422.69 دلار** در برابر **15,696.05 دلار**. این به‌معنای اثبات علت‌ومعلولی نیست؛ فقط نشان می‌دهد که باید زمان و بودجهٔ validation ابتدا روی retention متمرکز شود.[1]

> اصل اجرایی: هیچ تخفیف یا feature جدیدی به‌تنهایی «درمان churn» فرض نمی‌شود. هر اقدام باید یک فرضیه، گروه cohort، رفتار مورد انتظار، guardrail و معیار توقف داشته باشد.

## تعریف رفتارهایی که باید قبل از تمدید شکل بگیرند

کاربر یا تیمی که احتمال ماندگاری بیشتری دارد، باید در هفتهٔ اول حداقل یک workflow کامل را انجام دهد: import محلی، ایجاد یا review یک Contract، اجرای Quality Gate، تفسیر یک تصمیم Schema Drift، اتصال evidence به report/export، و در صورت policy مجاز، verification مستقل Signed Bundle. این «activation» نباید با نصب برنامه یا login اشتباه گرفته شود.

| نقطهٔ زمانی | رفتار مطلوب | instrument privacy-safe | اقدام در صورت فقدان رفتار |
|---|---|---|---|
| روز ۰ | `dataset_imported` و `contract_created` | pseudonymous tenant/user ID، UTC timestamp، outcome | راهنمای in-product و جلسهٔ ۱۵ دقیقه‌ای setup |
| ۲۴ ساعت | `checks_run` و نتیجهٔ `gate_blocked` یا pass | شمارندهٔ bounded و نوع outcome | پیام role-based برای حل اولین blocker |
| روز ۳ تا ۷ | `schema_baseline_approved` و `audit_exported` | event metadata-only | جلسهٔ reviewer برای وصل‌کردن evidence به deliverable واقعی |
| روز ۷ تا ۱۴ | `signed_bundle_verified` یا دلیل policy برای عدم اشتراک | outcome و reason category، بدون raw data | مسیر جایگزین audit export یا security review |
| هفتهٔ ۴ | Trusted Analysis Run تکرارشونده و Contract reuse | شمارندهٔ weekly cohort | بررسی executive sponsor یا تشخیص churn-risk |

Telemetry مرکزی فقط پس از تعیین consent، retention policy، tenant isolation، DSR و security review مجاز است؛ raw data، value rule یا secret هرگز در event ارسال نمی‌شود.[2]

## پنج تعدیل با بیشترین اولویت

### ۱. Onboarding را از «نصب» به یک مأموریت ۳۰ دقیقه‌ای قابل‌اتمام تبدیل کنید

**تغییر عملی:** اولین تجربه نباید با صفحهٔ تنظیمات یا feature tour آغاز شود. یک مسیر guided با عنوان «اولین گزارش مورداعتماد» بسازید که کاربر را به ترتیب از import محلی، انتخاب/ایجاد Contract، اجرای Gate، review نتیجه و export evidence عبور دهد. UI باید نشان دهد که هر مرحله چه output قابل‌استفاده‌ای برای report دارد؛ نه اینکه فقط یک چک‌لیست feature باشد.

**فرضیه:** اگر Time to First Trusted Report در workflow واقعی به کمتر از ۳۰ دقیقه برسد، احتمال رسیدن cohort به Contract reuse و weekly Trusted Analysis Run افزایش می‌یابد.

**KPI و guardrail:** نرخ completion مأموریت، median زمان، evidence completion و درصد کاربرانی که ظرف ۷ روز دوباره Gate اجرا می‌کنند. راهنما نباید raw dataset را به بیرون از boundary محلی ارسال کند.

### ۲. «تحویل به reviewer» را بخش استاندارد onboarding قرار دهید

**تغییر عملی:** پس از اولین Gate، کاربر نباید تنها بماند. یک handoff مشخص برای reviewer یا security owner داشته باشید: bundle یا audit export، نحوهٔ verify، محدودیت privacy، و یک جلسهٔ ۲۰ دقیقه‌ای review. برای Team و Enterprise، champion و reviewer هر دو باید در pilot charter نام‌دار باشند.

**فرضیه:** وقتی evidence به یک artifact واقعی و یک reviewer مشخص وصل شود، ارزش محصول از ابزار فردی به workflow تیمی منتقل و churn کاهش می‌یابد.

**KPI و guardrail:** نسبت accountهایی که تا روز ۱۴ حداقل یک reviewer action دارند، verification completion، review-cycle reduction و engagement هر دو نقش. اگر policy مشتری اشتراک bundle را ممنوع کند، مسیر audit export محلی جایگزین شود؛ نبود verification به‌تنهایی failure نیست، مگر آنکه workflow آن را لازم بداند.

### ۳. tier Professional را ساده نگه دارید؛ تخفیف را به activation و commitment گره بزنید

**تغییر عملی:** قیمت ماهانهٔ ۳۹ دلار را در آزمون نگه دارید و به‌جای تخفیف دائمی، دو گزینهٔ شفاف ارائه کنید: monthly برای discovery کوتاه و annual برای کاربری که یک workflow trusted را تکمیل کرده است. annual discount پیشنهادی فقط یک **hypothesis** برای آزمایش است؛ برای مثال ۱۰ تا ۱۵٪ تخفیف در ازای commitment سالانه، نه کاهش بی‌قیدوشرط قیمت پایه.

**فرضیه:** کاربری که پیش از پیشنهاد annual، یک Contract را reuse و یک evidence deliverable تولید کرده است، با احتمال بیشتری ارزش recurring را می‌بیند؛ در نتیجه discount به جای خرید کوتاه‌مدتِ ارزان، retention را تقویت می‌کند.

**KPI و guardrail:** conversion از monthly به annual پس از activation، usage در ۳۰/۶۰/۹۰ روز، refund/cancellation، و تفاوت retention میان discount-earned و discount-unconditional. از استفاده از annual contract برای پنهان‌کردن عدم‌استفاده پرهیز شود.

### ۴. Team را با «pilot قابل‌اعتبار به قرارداد» وارد کنید، نه با تخفیف عمومی ACV

**تغییر عملی:** Team/Business با ACV برنامه‌ریزی‌شدهٔ ۵٬۰۰۰ دلار باقی بماند؛ برای qualification قوی، یک **Team Evidence Pilot** چهار تا دوازده‌هفته‌ای با ورودی پیشنهادی ۳٬۰۰۰ دلار طراحی شود که هزینهٔ آن در صورت تبدیل به قرارداد سالانه اعتبار بگیرد. خروجی pilot باید سه workflow واقعی، یک template قابل‌استفادهٔ مجدد، یک reviewer handoff و یک تصمیم خرید مستند باشد.

**فرضیه:** کاهش ریسک تصمیم و ارائهٔ success plan مشخص، از کاهش بی‌قیدوشرط ACV در جلوگیری از churn مؤثرتر است؛ زیرا مشتری نخست ارزش تیمی و ownership workflow را تجربه می‌کند.

**KPI و guardrail:** pilot-to-paid، تعداد Trusted Analysis Run هفتگی در workspace، Contract reuse، completion reviewer و cycle زمان procurement. pilot بدون sponsor یا dataset واقعی پذیرفته نشود؛ در غیر این صورت هزینهٔ onboarding بدون signal تجاری افزایش می‌یابد.

### ۵. Enterprise onboarding را milestone-based و پس از qualification قیمت‌گذاری کنید

**تغییر عملی:** onboarding fee برنامه‌ریزی‌شدهٔ ۷٬۵۰۰ دلار را به deliverableهای شفاف پیوند دهید: architecture discovery، data boundary، SSO/security requirement mapping، pilot charter، key ownership و verifier workflow. پیش از روشن‌شدن sponsor، security owner و procurement path، custom integration یا تعهد KMS/HSM ندهید.

**فرضیه:** وضوح scope و نقطهٔ تصمیم، late-stage churn ناشی از security surprise یا هزینهٔ پنهان onboarding را کاهش می‌دهد.

**KPI و guardrail:** زمان از qualified discovery تا pilot charter، security blocker resolution، onboarding completion و renewal/expansion. Enterprise ACV یا onboarding را بدون ثبت win rate، cycle length و cost-to-serve افزایش ندهید؛ حساسیت ACV در مدل، اثر conversion را پوشش نمی‌دهد.[1]

## توالی اجرای ۶۰ روزه

| بازه | اقدام اصلی | مالک پیشنهادی | شاهد خروج |
|---|---|---|---|
| هفتهٔ ۱ | تعریف event schema و activation mission | Product + Security | taxonomy privacy-safe و consent review |
| هفتهٔ ۲ | ساخت/پروتوتایپ guided first trusted report | Product + Design | completion funnel و baseline زمان |
| هفتهٔ ۳ | اجرای پنج interview و سه pilot charter | Founder/PM + Sales | sponsor، deliverable و success measure نام‌دار |
| هفتهٔ ۴ | reviewer handoff و weekly risk review | Customer Success + Security | evidence completion و blocker log |
| هفتهٔ ۵ تا ۶ | آزمایش monthly/annual after-activation و Team Pilot | Sales + Product | proposal response، cohort usage و cancellation reason |
| هفتهٔ ۷ تا ۸ | تصمیم scale، iterate یا stop | مدیر محصول + sponsor اقتصادی | memo با Go/Narrow/Pivot/Stop |

## سیاست تشخیص زودهنگام churn-risk

Accountی که تا روز ۷ هیچ `checks_run` یا `contract_created` ندارد، account «فعال نشده» است، نه account دارای churn. Accountی که activation را تکمیل کرده اما تا هفتهٔ ۳ trusted run یا reviewer action ندارد، برای outreach شخصی اولویت دارد. Accountی که usage دارد اما هیچ owner اقتصادی یا proposal path ندارد، برای Go evidence کافی تولید نمی‌کند. هر reason باید در taxonomy کنترل‌شده ثبت شود: `time_to_value`، `workflow_fit`، `reviewer_adoption`، `security_policy`، `pricing_value`، `integration_gap` یا `no_economic_owner`.

## معیارهای decision gate

| شرط | Green | Yellow | Red |
|---|---|---|---|
| Time to First Trusted Report | کمتر از ۳۰ دقیقه | ۳۰ تا ۶۰ دقیقه | بیش از ۶۰ دقیقه |
| Evidence completion در pilot | بیش از ۸۰٪ | ۵۰ تا ۸۰٪ | کمتر از ۵۰٪ |
| Contract reuse در هفتهٔ چهارم | بیش از ۵۰٪ | ۲۵ تا ۵۰٪ | کمتر از ۲۵٪ |
| Reviewer handoff تا روز ۱۴ | بیش از ۶۰٪ accountهای qualified | ۳۰ تا ۶۰٪ | کمتر از ۳۰٪ |
| Sponsor / proposal | دو یا بیشتر | یک مورد | صفر |
| ۹۰ روز | Go یا Narrow | Narrow یا Pivot | Pivot یا Stop |

این آستانه‌ها policy پیشنهادی برای یادگیری‌اند و پیش از مشاهدهٔ cohort واقعی، SLA یا تضمین تجاری محسوب نمی‌شوند.

## آنچه نباید انجام شود

کاهش عمومی قیمت Professional یا Team بدون evidence از مانع قیمت، تخفیف Enterprise پیش از qualification امنیتی، افزودن featureهای platform-scale به‌خاطر درخواست تک‌مشتری، یا فعال‌سازی telemetry حساس بدون consent و review، همگی تصمیم‌هایی هستند که می‌توانند retention ظاهری یا ریسک عملیاتی ایجاد کنند بدون آنکه تناسب محصول-بازار را بهتر کنند.

## منابع

[1] `PRICE_AND_CHURN_SENSITIVITY_ANALYSIS_FA.md`، مدل برنامه‌ریزی DataSense، ۱۴ اوت ۲۰۲۶.

[2] `GTM_PILOT_AND_MEASUREMENT_PLAN_FA.md`، بخش instrumentation و حریم خصوصی، ۱۴ اوت ۲۰۲۶.
