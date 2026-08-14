# راهنمای مصاحبهٔ مشتری برای تصمیم Go / Narrow / Pivot / Stop

## هدف و اصل اجرا

این گفت‌وگو برای فروش feature یا گرفتن تأیید فرضیه نیست. هدف، جمع‌آوری شاهد رفتاری دربارهٔ مسئله، workflow، authority، willingness-to-pay و تناسب راهبرد DataSense است. مصاحبه‌گر نباید پیش از شنیدن یک incident واقعی، محصول، قیمت یا roadmap آینده را ارائه کند. هر پاسخ باید با یک رخداد، artifact، نقش یا زمان مشخص پیگیری شود.

> اصل اعتبار: «این قابلیت مفید به نظر می‌رسد» evidence نیست. Evidence شامل یک مثال واقعی، صاحب مسئله، deliverable مشخص، مسیر خرید و یک رفتار قابل مشاهده در pilot است.

## دادهٔ ثبت پیش از مصاحبه

| فیلد | مقدار ثبت‌شونده | دلیل |
|---|---|---|
| شرکت و vertical | نام، صنعت، اندازهٔ تقریبی تیم | تشخیص pattern برای Narrow یا vertical wedge |
| نقش مصاحبه‌شونده | کاربر، champion، reviewer، sponsor یا buyer | جداسازی pain user از authority خرید |
| workflow هدف | report/export، زمان‌بندی و data source | سنجش تناسب evidence-first |
| وضعیت جلسه | discovery، pilot review، pricing یا security | جلوگیری از ترکیب stageهای مختلف |
| سطح محرمانگی | محدودیت data، recording و follow-up | رعایت boundary مشتری |

## متن شروع جلسه — ۶۰ ثانیه

«هدف من امروز فروش محصول یا گرفتن تأیید نیست. می‌خواهم آخرین workflow واقعی شما را بفهمم؛ به‌ویژه جایی که کیفیت داده، evidence یا حساسیت اطلاعات گزارش را کند یا پرریسک کرده است. اگر پاسخ دقیق ندارید یا این مسئله برای شما اولویت ندارد، همان پاسخ نیز برای ما مفید است. آیا اجازه دارید دربارهٔ یک مثال واقعی، بدون به‌اشتراک‌گذاشتن دادهٔ حساس، صحبت کنیم؟»

## بخش ۱: Incident واقعی و شدت مسئله

| پرسش دقیق | follow-up اجباری | signal قوی | signal ضعیف |
|---|---|---|---|
| ۱. آخرین باری که report یا export به‌علت کیفیت، definition KPI یا دادهٔ حساس به چالش خورد، دقیقاً چه زمانی بود؟ | کدام deliverable، چه کسی متوجه شد و چه اتفاقی افتاد؟ | مثال با تاریخ، owner و اثر مشخص | پاسخ فرضی یا کلی |
| ۲. اثر آن incident چه بود؟ | ساعت بازکاری، تأخیر تصمیم، ریسک audit یا مشتری ناراضی را جدا کنید. | هزینه/ریسک قابل بیان | «کمی دردسر داشت» بدون اثر |
| ۳. چه چیزی باید قبل از انتشار معلوم می‌شد که معلوم نبود؟ | quality، schema، lineage، PII یا approval را اولویت‌بندی کنید. | یک gap روشن و قابل تکرار | feature list پراکنده |
| ۴. این رخداد چند بار در ۹۰ روز گذشته رخ داده است؟ | هر بار با همان workflow بود؟ | تکرار و pattern | تک‌رخداد غیرقابل‌تکرار |
| ۵. اگر این مسئله فردا حل نشود، چه کسی بیشترین هزینه را می‌دهد؟ | role و business consequence را نام ببرید. | owner اقتصادی یا عملیاتی روشن | «همه» یا «IT» بدون مالک |

## بخش ۲: Workflow فعلی و evidence

| پرسش دقیق | follow-up اجباری | signal قوی | signal ضعیف |
|---|---|---|---|
| ۶. از لحظهٔ دریافت dataset تا انتشار خروجی، مراحل واقعی چیست؟ | چه کسی در هر مرحله کار یا approval می‌دهد؟ | workflow قابل رسم | شرح ابزارها بدون جریان کار |
| ۷. امروز evidence کیفیت را کجا و چگونه نگه می‌دارید؟ | فایل، spreadsheet، ticket، email یا platform؟ | workaround زمان‌بر و پراکنده | evidence موجود، سریع و مورداعتماد |
| ۸. در workflow شما چه چیزی report را block می‌کند؟ | چه کسی authority توقف دارد؟ | quality/policy/security با authority روشن | هیچ gate یا authority وجود ندارد |
| ۹. اگر schema تغییر کند یا rule fail شود، چه تصمیمی می‌گیرید؟ | impact analysis و escalation چگونه انجام می‌شود؟ | رفتار استاندارد و نیاز به automation | پاسخ ad hoc اما بدون هزینه |
| ۱۰. reviewer برای اعتماد به خروجی چه artifactی می‌خواهد؟ | نمونهٔ metadata مجاز یا ساختار آن را شرح دهید. | artifact مشخص و قابل‌تحویل | «یک گزارش بهتر» بدون تعریف |
| ۱۱. چه مقدار از این workflow روی desktop/فایل/extract محلی انجام می‌شود؟ | کدام بخش نمی‌تواند cloud را ترک کند؟ | boundary سازگار با local-first | platform cloud مرکزی از قبل کل جریان را پوشش می‌دهد |

## بخش ۳: نقش‌ها، authority و procurement

| پرسش دقیق | follow-up اجباری | signal قوی | signal ضعیف |
|---|---|---|---|
| ۱۲. کاربر روزانه، champion، reviewer و buyer چه کسانی‌اند؟ | نام نقش و مسئولیت هر کدام را ثبت کنید. | نقش‌های متمایز و قابل‌دسترسی | یک نفر برای همهٔ نقش‌ها بدون authority |
| ۱۳. برای شروع pilot چه کسی باید بله بگوید؟ | security، IT یا data owner چه نقشی دارند؟ | مسیر approval روشن | «بعداً پیدا می‌کنیم» |
| ۱۴. اگر pilot موفق باشد، خرید از کدام budget یا فرآیند انجام می‌شود؟ | owner اقتصادی و بازهٔ زمانی تصمیم را بپرسید. | budget path و buyer نام‌دار | علاقه بدون مسیر خرید |
| ۱۵. چه objectionی می‌تواند pilot یا خرید را متوقف کند؟ | آن objection را به control یا policy مشخص ترجمه کنید. | blocker مشخص و قابل‌پاسخ | فهرست مبهم از featureها |
| ۱۶. برای یک proof موفق، چه security evidence لازم است؟ | SSO، key management، deployment یا data residency را اولویت دهید. | requirement صریح و owner امنیتی | درخواست «enterprise-grade» بدون تعریف |

## بخش ۴: آزمون ارزش و قیمت — فقط پس از فهم مسئله

ابتدا یک prototype یا workflow واقعی Trust Center را نشان دهید؛ سپس پرسش‌های زیر را بپرسید. قابلیت آینده را وعده ندهید. اگر requirement فعلی وجود ندارد، آن را به‌عنوان discovery ثبت کنید، نه commitment.

| پرسش دقیق | follow-up اجباری | signal قوی | signal ضعیف |
|---|---|---|---|
| ۱۷. کدام بخش از این workflow، incident قبلی شما را تغییر می‌داد؟ | دقیقاً کدام مرحله و چه artifactی؟ | اتصال به incident واقعی | «همه‌چیز مفید است» |
| ۱۸. چه چیزی مانع استفادهٔ هفتگی شما می‌شود؟ | integration، UX، policy، skill یا trust را رتبه‌بندی کنید. | blocker actionable | درخواست‌های زیاد و بی‌اولویت |
| ۱۹. اگر evidence bundle قابل verify باشد، چه کسی آن را مصرف می‌کند؟ | نام reviewer و محل استفاده در process را بپرسید. | مصرف‌کنندهٔ واقعی و verification flow | هیچ مصرف‌کننده‌ای مشخص نیست |
| ۲۰. برای Professional با بازهٔ ۲۹ تا ۴۹ دلار در ماه، واکنش شما چیست؟ | «در چه شرطی می‌خرید یا نمی‌خرید؟» | threshold و دلیل اقتصادی | فقط «گران/ارزان» |
| ۲۱. برای Team با ۳٬۰۰۰ تا ۹٬۰۰۰ دلار سالانه، چه value یا کنترل‌هایی باید دیده شود؟ | workspace، template، support یا review را رتبه‌بندی کنید. | خرید مشروط و measurable | درخواست discount بدون value case |
| ۲۲. اگر Enterprise نیازمند SSO/security review باشد، چه ACV و onboarding structure منطقی است؟ | چه کسی proposal را ارزیابی می‌کند و cycle چه‌قدر است؟ | buyer و process مشخص | پاسخ بدون authority |

## بخش ۵: تعهد pilot و خاتمه

| پرسش دقیق | follow-up اجباری | signal قوی | signal ضعیف |
|---|---|---|---|
| ۲۳. آیا حاضر هستید یک dataset و deliverable واقعی، بدون خروج raw data از boundary شما، برای pilot چهار‌هفته‌ای معرفی کنید؟ | owner، زمان آغاز و success measure را ثبت کنید. | تعهد مشخص | علاقه بدون قدم بعدی |
| ۲۴. در هفتهٔ چهارم، چه evidence باعث می‌شود بگویید ادامه می‌دهیم یا نمی‌دهیم؟ | معیار را با زبان مشتری یادداشت کنید. | success/failure definition روشن | «ببینیم چه می‌شود» |
| ۲۵. اگر pilot موفق بود، گام بعدی، owner و تاریخ تصمیم چیست؟ | proposal، security review یا procurement را مشخص کنید. | next step زمان‌دار | هیچ action بعدی |

متن پایان جلسه: «برای اطمینان از برداشت درست، incident، workflow، blocker و معیار تصمیمی که گفتید را خلاصه می‌کنم. آیا این جمع‌بندی دقیق است؟ اگر بله، ظرف ۴۸ ساعت یک pilot charter با success measure و boundary data ارسال می‌کنیم؛ اگر نه، فرضیهٔ خود را اصلاح می‌کنیم و feature یا قیمت جدیدی را به شما تحمیل نمی‌کنیم.»

## Scorecard پس از مصاحبه

هر محور با ۰ تا ۲ امتیاز ثبت می‌شود: ۰ = absent/مبهم، ۱ = جزئی یا بدون authority، ۲ = رفتار یا owner مشخص و قابل پیگیری. امتیاز برای اولویت‌بندی است، نه جایگزین judgment تیم.

| محور | ۰ | ۱ | ۲ |
|---|---|---|---|
| شدت و تکرار pain | مسئله فرضی | incident منفرد | incident تکراری با هزینه/ریسک روشن |
| تناسب workflow | evidence-first بی‌ربط | ارزش محدود | report/export حساس با gap evidence |
| adoption | کاربر نامشخص | علاقه به demo | champion و usage هفتگی محتمل |
| authority | buyer نامشخص | sponsor جزئی | sponsor اقتصادی و process خرید روشن |
| willingness-to-pay | فقط discount | price reaction مبهم | threshold/شرط خرید و proposal path روشن |
| تناسب امنیتی | requirement نامشخص | blocker قابل‌کشف | policy و owner security مشخص |

حداکثر امتیاز ۱۲ است. امتیاز ۹ تا ۱۲، به‌شرط وجود dataset واقعی و sponsor، candidate پایلوت محسوب می‌شود. امتیاز ۶ تا ۸ فقط برای discovery یا Narrow بررسی می‌شود. امتیاز کمتر از ۶ برای pilot مناسب نیست. این آستانه‌ها policy داخلی پیشنهادشده‌اند و باید پس از ۱۰ مصاحبه با دادهٔ واقعی بازتنظیم شوند.

## منطق تجمیعی Go / Narrow / Pivot / Stop

| نتیجه | evidence تجمیعی لازم | تفسیر |
|---|---|---|
| **Go** | دست‌کم دو pilot با usage تکرارشونده در هفتهٔ چهارم، دو sponsor اقتصادی، یک یا بیشتر proposal قابل‌قبول، blocker مشترک و scorecard قوی | pain، use و خرید هم‌زمان دیده می‌شوند؛ می‌توان vertical message و motion فروش را توسعه داد. |
| **Narrow** | scorecard و usage قوی، اما فقط در یک workflow/vertical یا یک persona تکرار می‌شود | evidence برای product وجود دارد، اما market definition بیش از حد وسیع بوده است. |
| **Pivot** | pain و usage اولیه وجود دارد، اما customer آن را budget line مستقل نمی‌داند یا incumbent را تنها پاسخ قابل‌قبول می‌داند | مسئله را حفظ کنید؛ packaging/positioning یا channel را عوض کنید. |
| **Stop** | incidentهای کم‌اهمیت، champion/sponsor نامشخص، pilot commitment ضعیف و reaction قیمت بدون مسیر خرید | نه مسئلهٔ فوری و نه مسیر اقتصادی وجود دارد؛ feature investment را متوقف کنید. |

## قواعد کیفیت دادهٔ مصاحبه

محتوای raw dataset، secret، customer PII یا credential را در transcript ثبت نکنید. نقل‌قول‌ها را با نقش و vertical pseudonymize کنید. هر claim خرید را با یک follow-up زمان‌دار یا artifact مانند pilot charter، security questionnaire یا proposal review اعتبارسنجی کنید. نتیجهٔ «Go» بدون یک یا چند دلیل مستند برای عدم خرید نیز ناقص است، زیرا علت رد برای pricing و positioning به‌اندازهٔ conversion ارزش یادگیری دارد.
