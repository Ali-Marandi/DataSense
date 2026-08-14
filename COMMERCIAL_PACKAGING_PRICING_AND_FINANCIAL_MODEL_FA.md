# بسته‌بندی، قیمت‌گذاری و مدل مالی برنامه‌ریزی DataSense

**تاریخ مرجع:** ۱۴ اوت ۲۰۲۶

## اصل تصمیم

قیمت‌گذاری DataSense هنوز نباید به‌عنوان «قیمت بازار اثبات‌شده» معرفی شود. در بازار هدف، ابزارهای platform مانند Alteryx و KNIME و ابزارهای data-quality مانند Soda و Great Expectations، دامنه، deployment و مدل فروش متفاوتی دارند.[1] [2] [3] [4] بنابراین، اعداد این سند **فرضیهٔ قابل‌آزمون برای pilot** هستند، نه benchmark قطعی یا forecast قابل‌اتکا.

> قاعدهٔ قیمت: مشتری نباید برای یک فهرست feature پرداخت کند؛ باید برای کاهش ریسک انتشار تحلیل، تکرارپذیری evidence و سرعت review پرداخت کند.

## معماری بسته‌بندی

| بسته | مشتری و job-to-be-done | پیشنهاد ارزش | مدل تجاری پیشنهادی | وضعیت |
|---|---|---|---|---|
| Community Desktop | تحلیل‌گر مستقل یا ارزیابی‌کننده | تحلیل محلی، PII scan، Contract، Quality Gate و export audit پایه | رایگان؛ محدودیت هدفمند در همکاری/automation | مسیر acquisition و proof-of-value |
| Professional | analyst حرفه‌ای یا تیم کوچک | templateهای دامنه، signed evidence محلی، workflow history، export پیشرفته و پشتیبانی استاندارد | per-user یا per-workspace سالانه | **آزمایش قیمت** |
| Team / Business | تیم داده با workflow مشترک | template مشترک، review workflow سبک، integration pack، scheduler محدود و support سریع‌تر | حداقل seat یا workspace annual | **بعد از evidence retention** |
| Enterprise | سازمان حساس به داده | SSO/RBAC، private deployment، audit retention، policy، onboarding و SLA قراردادی | annual contract + خدمات onboarding | فقط پس از acceptance امنیتی و عملیات |

Community نباید از نظر کیفیت یا safety عمداً محصول ناقص باشد؛ هدف این tier نمایش ارزش محلی در کمتر از پنج دقیقه است. تفاوت پولی باید روی reuse تیمی، automation، evidence سطح بالاتر، پشتیبانی و deployment باشد، نه روی تحمیل ریسک مصنوعی به کاربر رایگان.

## آزمون قیمت و بسته‌بندی

| آزمایش | cohort | پیشنهاد آزمایشی | فرضیه | معیار تصمیم |
|---|---|---|---|---|
| A: Professional self-serve | analystهای pilot انگلیسی‌زبان | بازهٔ ماهانهٔ ۲۹ تا ۴۹ دلار به‌ازای هر کاربر، با تخفیف سالانه | نیاز evidence ارزش پرداخت فردی دارد. | conversion از trial به پرداخت و استفادهٔ هفتهٔ چهارم. |
| B: Team annual | تیم ۳ تا ۲۵ نفره | بازهٔ سالانهٔ ۳٬۰۰۰ تا ۹٬۰۰۰ دلار برای workspace، متناسب با support/template | خریدار برای استانداردسازی و reuse تیمی پول می‌دهد. | وجود champion + budget owner و cycle فروش. |
| C: Enterprise discovery | سازمان دارای security review | قرارداد design-partner بدون قیمت لیست قطعی؛ ACV هدف در مدل برنامه‌ریزی ۱۸ تا ۴۵ هزار دلار | SSO و signed evidence blocker واقعی procurement هستند. | حداقل دو partner آن را critical بنامند و به security review وارد شوند. |

این بازه‌ها «قیمت اعلامی» نیستند. تنها پس از ۱۰ گفت‌وگوی price-sensitive و حداقل پنج proposal واقعی باید قیمت فهرست یا discount policy اعلام شود. آزمون A با fake-door یا landing page مجاز است، به شرط آنکه capabilityهای وعده‌داده‌شده شفاف و قابل‌تحویل باشند.

## مدل درآمد چندلایهٔ متمرکز

در مرحلهٔ نخست، تمرکز باید روی دو جریان باشد: subscription Professional/Team و annual Enterprise. onboarding یا implementation fee فقط برای جبران هزینهٔ واقعی راه‌اندازی و کاهش ریسک مشتری enterprise به کار رود؛ نباید به درآمد پیچیده یا وابستگی خدماتی تبدیل شود. API، connector marketplace، white-label و data products در این مرحله **Later** هستند؛ زیرا هنوز demand، governance و unit economics آن‌ها اثبات نشده است.

| جریان | اولویت | منطق | ریسک |
|---|---:|---|---|
| Professional subscription | Now | چرخه feedback کوتاه و سنجش activation/retention | churn بالا اگر ارزش تکرارشونده روشن نباشد. |
| Team workspace annual | Next | ARPU بالاتر و همکاری/template به‌عنوان switching cost مشروع | نیازمند collaboration ساده و support قابل‌مقیاس. |
| Enterprise annual + onboarding | Now، به‌صورت design partner | بودجهٔ بالاتر و اعتبار security requirement | cycle فروش بلند، implementation burden و feature gap. |
| Template packs صنعتی | Next | رشد ARPU با ارزش مشخص برای vertical | قبل از evidence vertical نباید ساخته شود. |
| Marketplace/API/white-label | Later | اهرم distribution بالقوه | overengineering و ریسک security/compliance. |

## مدل مالی برنامه‌ریزی

workbook همراه، یک مدل driver-based پنج‌ساله برای سناریوهای Downside، Base و Upside است. مدل historical financial ندارد، زیرا DataSense یک کسب‌وکار خصوصی با دادهٔ مالی ارائه‌نشده است. تمام سلول‌های ورودی با آبی و یادداشت «Planning assumption — validation required» مشخص شده‌اند. فرمول‌ها از تب Assumptions تغذیه می‌شوند و به‌هیچ‌وجه نباید به‌عنوان projection سرمایه‌گذاری یا commitment درآمد استفاده شوند.

| driver | Downside | Base | Upside | معنا |
|---|---:|---:|---:|---|
| رشد سالانهٔ seat Professional | ۴۰٪ | ۸۰٪ | ۱۳۰٪ | پس از سال اول؛ قابل‌جایگزینی با cohort واقعی. |
| رشد سالانهٔ Team logos | ۲۰٪ | ۶۰٪ | ۱۰۰٪ | رشد سالانهٔ لوگوها، نه سهم بازار. |
| Enterprise wins در سال اول | ۰ | ۱ | ۲ | قراردادهای جدید؛ به capacity فروش وابسته است. |
| نرخ churn سالانهٔ Professional | ۳۰٪ | ۲۰٪ | ۱۴٪ | برای planning؛ با retention cohort واقعی جایگزین شود. |
| Gross margin subscription | ۷۰٪ | ۷۸٪ | ۸۳٪ | فرض operating، نه benchmark. |

مدل از چهار بلوک درآمدی استفاده می‌کند: Professional MRR، Team annual contracts، Enterprise ACV و onboarding. هزینه‌ها در سه بلوک COGS، محصول/مهندسی و فروش/موفقیت مشتری مدل شده‌اند. خروجی‌ها revenue، gross profit، operating expense، EBITDA برنامه‌ریزی، ARR پایان‌سال، logo count، contribution margin و cash burn قبل از سرمایه‌گذاری/مالیات هستند.

## قواعد سرمایه و runway

تا قبل از اثبات سه معیار، رشد پرهزینه یا جذب سرمایه نباید تصمیم پیش‌فرض باشد: pilot-to-paid conversion، retention پس از حداقل ۹۰ روز و contribution margin مثبت برای cohort جدید. Bootstrapping و design-partner revenue مسیر Safe است. قرارداد enterprise کوچک با onboarding محدود مسیر Smart است. سرمایه‌گذاری خارجی فقط زمانی قابل‌بحث است که funnel تکرارپذیر، ACV ثابت و چرخهٔ فروش قابل‌پیش‌بینی باشد.

| سناریو | تصمیم عملیاتی | trigger برای ادامه | trigger برای توقف یا pivot |
|---|---|---|---|
| Downside | حفظ تیم کوچک، discovery و product narrowing | حداقل یک design partner متعهد | conversion یا retention زیر معیار از پیش‌تعریف‌شده |
| Base | سرمایه‌گذاری در evidence/SSO و sales-assisted pilot | دو contract قابل‌تمدید و KPI trusted-run رشد کند | هزینهٔ acquisition از LTV planning فراتر رود |
| Upside | template vertical و channel partnership | repeatable pipeline و capacity support کافی | رشد support سریع‌تر از margin یا کیفیت محصول |

## معیارهای Go/No-Go برای قیمت نهایی

قیمت فهرست Professional فقط پس از مشاهدهٔ conversion و retention cohort تعریف می‌شود. قیمت Team فقط پس از مشاهدهٔ sponsor اقتصادی و reuse template تعریف می‌شود. قیمت Enterprise فقط بعد از هزینه‌گذاری واقعی SSO، security review، onboarding و support تعیین می‌شود. اگر مشتری صرفاً برای discount پاسخ مثبت نشان دهد، آن signal product-market fit نیست.

## کنترل تحویل workbook

Workbook `DATASENSE_COMMERCIAL_PLANNING_MODEL.xlsx` شامل پنج تب Assumptions، Revenue، Operating Model، KPIs و Sources است. audit ساختاری ۱۹۰ سلول فرمولی و یادداشت منبع روی inputهای اصلی را تایید کرد. workbook به شش صفحهٔ چاپی render شده است؛ با این حال، ارزش عددی آن کاملاً به اعتبارسنجی inputهای آبی با دادهٔ cohort، قیمت proposal واقعی و هزینهٔ عملیاتی وابسته است.

## منابع

[1]: https://www.alteryx.com/ "Alteryx — Unified Data Analytics Platform"
[2]: https://www.knime.com/knime-for-enterprise "KNIME — For Enterprise"
[3]: https://www.soda.io/ "Soda — Data Quality"
[4]: https://greatexpectations.io/ "Great Expectations — GX Core"
