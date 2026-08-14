# راهنمای تمرین و مدیریت پرسش‌وپاسخ دک اجرایی DataSense

**دک مرجع:** «DataSense: از تحلیل محلی تا Evidence قابل‌دفاع»

**مخاطب اصلی:** هیئت‌مدیره، CEO، CTO، CISO، sponsor اقتصادی و مدیران داده

**مدت ارائه:** ۱۰ تا ۱۲ دقیقه

**مدت Q&A پیشنهادی:** ۵ تا ۱۰ دقیقه
**اصل سخن‌گویی:** capability فعال را با evidence بیان کنید؛ فرضیه را فرضیه بنامید؛ requirement آینده را به شرط و owner مشخص گره بزنید.

## ۱. هدف تمرین

تمرین برای حفظ‌کردن متن نیست. هدف این است که ارائه‌دهنده بتواند سه پیام را بدون اتکا به اسلاید منتقل کند: نخست، DataSense output محلی را به evidence قابل‌دفاع تبدیل می‌کند؛ دوم، Signed Evidence integrity را اثبات می‌کند اما جایگزین KMS/HSM یا platform-wide access control نیست؛ و سوم، سرمایه‌گذاری بعدی تنها پس از مشاهدهٔ usage، buyer و willingness-to-pay هم‌زمان انجام می‌شود.

هر پاسخ باید به یکی از سه دستهٔ زیر ختم شود: **evidence موجود، فرضیهٔ در حال validation، یا تصمیم/owner بعدی**. اگر پاسخی در هیچ‌یک از این دسته‌ها نمی‌گنجد، احتمالاً ادعای مبهم یا roadmap ناخواسته است.

## ۲. آماده‌سازی پیش از جلسه

| بازه | اقدام | خروجی قابل‌مشاهده |
|---|---|---|
| ۲۴ ساعت قبل | نسخهٔ دک، notes، تحلیل حساسیت و یک‌صفحهٔ تصمیم را هم‌راستا کنید. | یک source of truth برای اعداد و اصطلاحات. |
| ۲ ساعت قبل | اعداد اصلی را با مدل تطبیق دهید: 573,511.10 دلار درآمد Base 2030، EBITDA برابر (141,921.84) دلار، و اثر ۲۰٪→۱۲٪ churn برابر 36,422.69 دلار EBITDA. | جلوگیری از پاسخ عددی متناقض. |
| ۳۰ دقیقه قبل | نقش‌های جلسه را تعیین کنید: presenter، پاسخ‌گوی فنی، پاسخ‌گوی امنیتی و timekeeper. | پاسخ‌ها کوتاه و بدون تداخل می‌مانند. |
| ۱۰ دقیقه قبل | bridge sentence و خط قرمز هر اسلاید را مرور کنید. | تمرکز روی پیام تصمیم، نه جزئیات. |

### سه دور تمرین پیشنهادی

**دور اول — روایت:** دک را بدون سؤال و در ۱۲ دقیقه ارائه کنید. تمرکز فقط روی انتقال، نه کمال ادبی. در این دور زمان هر اسلاید باید ثبت شود.

**دور دوم — اعداد و مرزها:** یک نفر نقش CFO و یک نفر نقش CISO را بازی کنند. ارائه‌دهنده باید هر عدد را با برچسب planning scenario و هر کنترل را با مرز capability فعلی بیان کند.

**دور سوم — قطع‌کردن و بازگشت:** بازبین در اسلایدهای ۳، ۴، ۶، ۸ و ۹ سؤال سخت بپرسد. ارائه‌دهنده باید پاسخ را در حداکثر ۳۰ تا ۴۵ ثانیه بدهد، سپس با جملهٔ bridge به پیام اسلاید بازگردد.

> معیار آمادگی: ارائه‌دهنده باید بتواند اسلایدهای ۳، ۴، ۶ و ۹ را بدون خواندن notes و بدون ادعای KMS، forecast یا price list ارائه کند.

## ۳. Cue sheet تمرین به‌تفکیک اسلاید

| اسلاید | زمان | cue آغاز | یک خط قرمز | bridge به بعد |
|---:|---:|---|---|---|
| ۱ | ۴۵ ثانیه | «این تصمیم محصولی و تجاری است، نه فهرست feature.» | نگویید محصول همهٔ governance platformها را جایگزین می‌کند. | «برای همین باید ارزش اقتصادی را اثبات کنیم.» |
| ۲ | ۷۵ ثانیه | «پایلوت، آزمون willingness-to-pay است؛ نه demo.» | usage را به‌تنهایی نشانهٔ PMF معرفی نکنید. | «قابلیتی که این آزمون را ممکن می‌کند Signed Evidence است.» |
| ۳ | ۹۰ ثانیه | «Artifact قابل‌انتقال، بدون کپی data.» | HMAC را «امضای عمومی برای همهٔ ممیزان» نگویید. | «حالا مرز این قابلیت را روشن می‌کنیم.» |
| ۴ | ۷۵ ثانیه | «شفافیت مرز، بخشی از اعتماد است.» | KMS/HSM یا RBAC platform-wide را active معرفی نکنید. | «با این مرز، پایلوت قابل‌تعریف می‌شود.» |
| ۵ | ۹۰ ثانیه | «نصب موفق، موفقیت مشتری نیست.» | KPIهای یادگیری را SLA معرفی نکنید. | «این evidence، مبنای تصمیم ۹۰ روزه است.» |
| ۶ | ۹۰ ثانیه | «Stop یک شکست پنهان نیست؛ یادگیری کنترل‌شده است.» | Go را فقط با علاقهٔ verbal توجیه نکنید. | «pricing نیز باید به همین روش validate شود.» |
| ۷ | ۷۵ ثانیه | «این‌ها price hypothesis هستند.» | قیمت‌ها را price list ننامید. | «حالا دامنهٔ مالی این فرضیه‌ها را می‌بینیم.» |
| ۸ | ۹۰ ثانیه | «این نمودار forecast نیست؛ دامنهٔ ریسک اجراست.» | Upside را هدف تضمین‌شده معرفی نکنید. | «سودآوری همان ریسک را شفاف‌تر می‌کند.» |
| ۹ | ۹۰ ثانیه | «Retention lever قوی‌تر از price-only است.» | کاهش churn را علت اثبات‌شده یا تضمین‌شده نگویید. | «برای اثبات آن، برنامهٔ ۹۰ روزه داریم.» |
| ۱۰ | ۷۵ ثانیه | «درخواست ما، مجوز یادگیری منضبط است.» | ادامهٔ ساخت platform-scale را قبل از gate تایید نکنید. | «اکنون خوشحال می‌شوم به سؤال‌ها پاسخ دهیم.» |

## ۴. پاسخ‌گویی به پرسش‌های دشوار

### الف) فنی و امنیتی

| پرسش محتمل | پاسخ کوتاه پیشنهادی | evidence یا اقدام بعدی |
|---|---|---|
| آیا HMAC برای enterprise کافی است؟ | برای pilot محلی که signer و verifier key مشترک مجاز دارند، HMAC integrity و tamper detection را فراهم می‌کند. برای ممیز خارجی یا اشتراک گسترده، امضای نامتقارن یا KMS-managed signature پس از threat model لازم است. | guide Signed Evidence و security discovery. |
| آیا bundle دادهٔ حساس را به بیرون می‌فرستد؟ | طراحی export، cell value، value پارامتر rule و مسیر فایل محلی را حذف می‌کند؛ با این حال metadata ممکن است حساس باشد و policy مشتری باید قبل از اشتراک اعمال شود. | privacy boundary و policy review. |
| چرا KMS/HSM را الآن نمی‌سازید؟ | بدون تعیین ownership کلید، data boundary و integration مشتری، ساخت کنترل عمومی ریسک تعهد نادرست دارد. این requirement در discovery با owner امنیتی ثبت می‌شود. | architecture discovery milestone. |
| آیا محصول جایگزین Purview یا platform داده است؟ | نه. wedge ما این است که output تحلیلی desktop را به evidence قابل‌دفاع تبدیل کنیم، نه replacement کامل catalog یا governance platform. | positioning و workflow واقعی pilot. |
| آیا SSO آماده است؟ | Control Plane و SAML/RBAC پایه وجود دارد، اما تعهد production برای مشتری خاص فقط پس از security/SSO discovery و acceptance criteria داده می‌شود. | technical validation با customer owner. |

### ب) تجاری و بازار

| پرسش محتمل | پاسخ کوتاه پیشنهادی | evidence یا اقدام بعدی |
|---|---|---|
| چرا مشتری باید برای evidence پول بدهد؟ | هنوز فرض نمی‌کنیم که می‌دهد. pilot روی incident واقعی، report واقعی، reviewer و budget path طراحی شده تا نشان دهد evidence زمان review، risk یا بازکاری را تغییر می‌دهد یا نه. | pilot charter و proposal response. |
| چرا اکنون قیمت را کم نمی‌کنید؟ | در مدل، retention Professional در محدودهٔ بررسی‌شده lever قوی‌تری از price-only است. تخفیف عمومی می‌تواند value signal را مخدوش کند؛ price test باید بعد از activation و با guardrail انجام شود. | cohort conversion و cancellation reason. |
| چرا Team Pilot سه‌هزار دلاری پیشنهاد می‌شود؟ | آن یک price hypothesis است، نه تخفیف عمومی. هدف، کاهش ریسک تصمیم و تبدیل هزینهٔ pilot به اعتبار قرارداد سالانه، در ازای workflow واقعی و sponsor است. | pilot-to-paid و cost-to-serve. |
| اگر مشتری featureهای بیشتری بخواهد چه می‌کنید؟ | درخواست را به conversion، retention یا evidence completion وصل می‌کنیم. اگر فقط در یک vertical تکرار شود، Narrow می‌کنیم؛ feature عمومی بدون evidence وارد backlog نمی‌شود. | interview scorecard و roadmap gate. |
| اگر incumbent مشتری همین قابلیت را دارد چه می‌کنید؟ | اگر gap مشخص و شدید وجود نداشته باشد، آن account qualification مناسب pilot نیست. اگر pain واقعی ولی purchase مستقل نیست، نتیجه Pivot به integration یا outcome عمودی است. | علت رد مستند. |

### ج) مالی و هیئت‌مدیره

| پرسش محتمل | پاسخ کوتاه پیشنهادی | evidence یا اقدام بعدی |
|---|---|---|
| آیا 573,511 دلار درآمد ۲۰۳۰ forecast است؟ | خیر. این خروجی سناریوی Base در مدل برنامه‌ریزی با فرضیات داخلی است؛ نه forecast، valuation یا guidance. | workbook و driverها. |
| چرا EBITDA Base هنوز منفی است؟ | مدل نشان می‌دهد که رشد و price-only کافی نیستند؛ retention، cost-to-serve و enterprise execution باید هم‌زمان validate شوند. | sensitivity و cohort metrics. |
| مهم‌ترین lever کدام است؟ | در grid بررسی‌شده، کاهش Professional churn از ۲۰٪ به ۱۲٪ در price پایه، EBITDA را 36,422.69 دلار بهتر می‌کند؛ افزایش قیمت ۲۰٪، 15,696.05 دلار. این اولویت validation را مشخص می‌کند، نه causality تضمین‌شده. | تحلیل حساسیت. |
| چه زمانی باید سرمایه‌گذاری بیشتری کنیم؟ | فقط در حالت Go: حداقل دو pilot تکرارشونده، sponsor اقتصادی، blocker مشترک و proposal قابل‌قبول. | memo روز ۹۰. |
| چه چیزی باعث Stop می‌شود؟ | adoption ضعیف به‌همراه نبود sponsor و مسیر خرید؛ در آن حالت feature investment متوقف و discovery با segment جدید شروع می‌شود. | scorecard و interview evidence. |

## ۵. الگوی پاسخ ۳۰ ثانیه‌ای

برای پاسخ به هر پرسش از الگوی **Answer → Evidence → Boundary → Next step** استفاده کنید.

> «پاسخ کوتاه این است که [پاسخ]. evidence فعلی ما [قابلیت/عدد/آزمون] است. مرز آن این است که [آنچه هنوز اثبات یا ساخته نشده]. گام بعدی ما [مالک، زمان یا معیار تصمیم] خواهد بود.»

**نمونه:** «پاسخ کوتاه این است که HMAC tamper detection قابل‌بررسی می‌دهد. evidence فعلی، bundle metadata-only و verifier مستقل است. مرز آن این است که برای ممیز خارجی key مشترک مناسب نیست. گام بعدی، threat model و انتخاب KMS یا asymmetric signature با security owner مشتری است.»

## ۶. تکنیک‌های bridge و مدیریت فشار جلسه

| وضعیت | جملهٔ bridge پیشنهادی |
|---|---|
| سؤال خارج از scope | «این requirement مهم است؛ امروز آن را capability فعال معرفی نمی‌کنیم. اجازه دهید آن را به owner و acceptance criterion مشخص تبدیل کنیم.» |
| درخواست عدد قطعی | «عدد موجود planning assumption است. برای عدد قابل‌تعهد به cohort و proposal واقعی نیاز داریم؛ در غیر این صورت، دقت ظاهری ایجاد می‌کنیم.» |
| فشار برای roadmap | «می‌توانیم آن را به roadmap وارد کنیم، اما پس از روشن‌شدن اثرش بر conversion، retention یا evidence completion.» |
| چالش دربارهٔ رقبا | «هدف ما replacement کل platform نیست؛ ابتدا باید wedge evidence برای output تحلیلی را با workflow واقعی اثبات کنیم.» |
| قطع‌کردن طولانی | «جمع‌بندی یک‌جمله‌ای این است: [پیام]. جزئیات را در follow-up با owner مربوطه می‌بندیم.» |

## ۷. red team rehearsal: سناریوهای تمرین اجباری

| نقش بازبین | سؤال یا اعتراض | پاسخ خوب چه ویژگی دارد؟ |
|---|---|---|
| CFO | «چرا بدون EBITDA مثبت، پایلوت اجرا کنیم؟» | می‌گوید pilot برای کاهش عدم‌قطعیت است و scale فروش قبل از gate انجام نمی‌شود. |
| CISO | «کلید کجا نگهداری می‌شود و چه کسی rotate می‌کند؟» | HMAC pilot را از KMS/HSM production جدا می‌کند و owner/security review می‌خواهد. |
| CTO | «چرا این را در platform فعلی خودمان نسازیم؟» | به time-to-trusted-report، workflow evidence و requirement واقعی بازمی‌گردد؛ وعدهٔ feature اضافی نمی‌دهد. |
| مدیر فروش | «اگر تخفیف ندهیم چگونه conversion می‌گیریم؟» | annual-after-activation و pilot credit را experiment با guardrail می‌نامد، نه policy قطعی. |
| عضو هیئت‌مدیره | «چه زمانی Stop می‌کنید؟» | معیارهای adoption، sponsor، proposal و evidence day-90 را با شفافیت بیان می‌کند. |

## ۸. چک‌لیست نهایی قبل از ورود به جلسه

- [ ] منبع اعداد مالی، ۱۴ اوت ۲۰۲۶، در دسترس است و presenter می‌داند که Base revenue و EBITDA چیست.
- [ ] presenter می‌تواند تفاوت HMAC و KMS/HSM/امضای نامتقارن را در ۳۰ ثانیه توضیح دهد.
- [ ] presenter می‌داند که قیمت‌ها hypothesis هستند، نه price list.
- [ ] owner پاسخ‌های امنیت، مالی و فروش در اتاق مشخص است.
- [ ] درخواست پایانی جلسه روی تأیید pilot و gate روز ۹۰ متمرکز است.
- [ ] هیچ‌کس capability آینده، integration سفارشی یا نتیجهٔ مالی را بدون شرط و acceptance criteria تعهد نمی‌دهد.

## منابع داخلی

[1] `DATASENSE_SIGNED_EVIDENCE_COMMERCIAL_PRESENTER_SCRIPT_FA.md`.

[2] `PRICE_AND_CHURN_SENSITIVITY_ANALYSIS_FA.md`.

[3] `GTM_PILOT_AND_MEASUREMENT_PLAN_FA.md`.

[4] `SIGNED_EVIDENCE_BUNDLE_GUIDE_FA.md`.
