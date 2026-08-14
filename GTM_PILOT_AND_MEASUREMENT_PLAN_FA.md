# برنامهٔ GTM، پایلوت و اندازه‌گیری DataSense

## هدف اجرایی

هدف ۹۰ روز نخست، «رشد ظاهری» یا افزودن قابلیت‌های بیشتر نیست. هدف، اثبات یا رد یک فرضیهٔ دقیق است: آیا تیمی که تحلیل جدولی حساس انجام می‌دهد، برای evidence محلی-اول پیش از report/export ارزش عملیاتی و اقتصادی قائل است؟ Data governance در اولویت پایدار CDAOها قرار دارد، اما اولویت سازمانی به‌تنهایی محصول-بازار متناسب یا willingness-to-pay یک محصول جدید را اثبات نمی‌کند.[1]

## ICP و معیار qualification

Ideal Customer Profile در مرحلهٔ نخست، تیم انگلیسی‌زبان تحلیل یا عملیات با ۵۰ تا ۵۰۰۰ کارمند است که گزارش دوره‌ای، دادهٔ جدولی حساس، یک owner کسب‌وکار و حداقل یک reviewer کیفیت/امنیت دارد. مشتری‌ای که از روز نخست catalog سراسری یا replacement کامل platform فعلی می‌خواهد، ICP این پایلوت نیست. معیار ورود باید از اشتیاق verbal فراتر برود و یک dataset قابل‌استفاده و یک deliverable واقعی داشته باشد.

| معیار | شرط پذیرش pilot | علت |
|---|---|---|
| مسئلهٔ واقعی | یک report/export واقعی که کیفیت یا evidence آن مهم است | demo با دادهٔ ساختگی evidence PMF نیست. |
| مالک | sponsor کسب‌وکار و champion کاربر نام‌دار | بدون owner، adoption و تصمیم خرید مبهم است. |
| data boundary | data خام local بماند یا policy انتقال روشن باشد | با positioning local-first سازگار است. |
| زمان | امکان اجرای چهار هفته‌ای با جلسهٔ هفته‌ای | feedback سریع و تصمیم‌پذیر می‌دهد. |
| economic path | دسترسی به budget owner یا فرآیند خرید | «کاربر خوشحال» بدون مسیر خرید، signal تجاری نیست. |

## برنامهٔ ۹۰ روزه

| بازه | deliverable | KPI/شاهد | معیار عبور |
|---|---|---|---|
| روز ۱ تا ۱۴ | ۱۵ مصاحبهٔ discovery، landing-page message test و shortlist design partner | ثبت مسئله، workflow، owner، blocker، budget path | حداقل ۵ مسئلهٔ تکرارشونده با زبان مشابه مشتری. |
| روز ۱۵ تا ۳۰ | سه pilot charter و baseline عملیاتی | زمان تهیه evidence، defect escape، review time و stakeholder map | سه dataset واقعی و deliverable مشخص. |
| روز ۳۱ تا ۶۰ | اجرای Trust Center، evidence export و Signed Bundle | time-to-first-trusted-report، contract reuse، blocked-run reason | دست‌کم دو pilot به استفادهٔ تکرارشونده برسند. |
| روز ۶۱ تا ۷۵ | security/SSO discovery و proposal test | blockerهای security، proposal response و buyer objection | حداقل دو sponsor economic identified. |
| روز ۷۶ تا ۹۰ | renewal/paid decision و roadmap review | pilot-to-paid یا دلیل رد مستند | تصمیم Go، Narrow، Pivot یا Stop. |

## مصاحبهٔ مسئله‌محور

مصاحبه نباید با demo آغاز شود. ابتدا از آخرین رویداد واقعی بپرسید: «آخرین بار که گزارش یا export شما به علت کیفیت، تعریف KPI یا دادهٔ حساس به چالش خورد چه رخ داد؟» سپس روشن کنید چه کسی کار را دوباره انجام داد، چه زمانی از بین رفت، چه evidence خواسته شد، چه کسی approval داشت و امروز چه ابزار یا workaroundی استفاده می‌شود. در پایان، بدون وعدهٔ capability آینده، workflow واقعی را با prototype یا Trust Center فعلی مرور کنید.

| سؤال | signal مثبت | signal منفی |
|---|---|---|
| آخرین incident چه زمانی بود؟ | مثال دقیق، اثر واقعی و owner روشن | پاسخ کلی یا مشکل فرضی |
| امروز چگونه evidence می‌سازید؟ | فایل/چک‌لیست/approval پراکنده و زمان‌بر | workflow موجود سریع و قابل‌دفاع است |
| چه چیزی release/report را block می‌کند؟ | quality، policy، security یا audit با authority مشخص | هیچ‌کس مسئول نیست یا issue بی‌هزینه است |
| چه کسی budget دارد؟ | sponsor و procurement path قابل‌نام‌بردن | «بعداً بررسی می‌کنیم» |
| چه چیزی باعث ترک ابزار فعلی می‌شود؟ | gap مشخص و شدید | درخواست feature list کلی |

## تعریف موفقیت پایلوت

پایلوت موفق صرفاً نصب موفق نیست. کاربر باید یک Contract را review، یک Quality Gate را اجرا، یک Schema Drift decision را تفسیر و یک evidence export را به artifact واقعی گزارش وصل کند. Signed Bundle فقط زمانی موفق است که reviewer مستقل بتواند آن را verify کند و policy مشتری اجازهٔ اشتراک metadata را بدهد.

| KPI | تعریف | هدف پیشنهادی برای یادگیری | تفسیر |
|---|---|---:|---|
| Time to First Trusted Report | import تا evidence/report قابل review | کمتر از ۵ دقیقه در demo و کمتر از ۳۰ دقیقه در workflow واقعی | بیشتر بودن نشانهٔ UX یا integration friction است. |
| Contract reuse rate | runهایی که contract موجود را دوباره استفاده می‌کنند / کل runهای معتبر | بیشتر از ۵۰٪ در هفته چهارم | reuse پایین یعنی contract ارزش عملیاتی یا fit ندارد. |
| Evidence completion rate | runهایی که Contract، Gate، fingerprint و audit metadata دارند | بیشتر از ۸۰٪ در deliverableهای pilot | کمتر بودن، مسیر محصول یا policy را ناقص نشان می‌دهد. |
| Review-cycle reduction | زمان review بعد از pilot نسبت به baseline | جهت کاهش، نه وعدهٔ درصد قطعی | با دادهٔ مشتری سنجیده شود. |
| Pilot-to-paid | pilotهای دارای proposal/contract / pilot کامل‌شده | حداقل ۱ تصمیم پرداخت یا عدم‌پرداخت مستند | نبود تصمیم، ضعف qualification یا value است. |

## instrumentation و حریم خصوصی

برای سنجش محصول، telemetry نباید raw data یا value rule را منتقل کند. حداقل eventها عبارت‌اند از `dataset_imported`، `contract_created`، `checks_run`، `gate_blocked`، `schema_baseline_approved`، `audit_exported` و `signed_bundle_verified`. payload هر event باید فقط identifier pseudonymous، timestamp UTC، نوع رویداد، outcome و شمارندهٔ bounded داشته باشد. پیش از فعال‌سازی telemetry مرکزی، consent/policy، retention، tenant isolation، DSR و security review تعیین شود.

> North Star Metric: **Trusted Analysis Runs هفتگی**؛ یعنی runی که contract/gate معتبر دارد و evidence قابل‌استفاده برای report یا export تولید کرده است. این معیار تنها در کنار outcome و retention ارزش دارد؛ افزایش مصنوعی تعداد run، موفقیت محصول نیست.

## رشد و کانال

رشد اولیه باید founder-led و evidence-led باشد. مسیر Safe، outreach مستقیم به network حرفه‌ای و communityهای analyst/BI است. مسیر Smart، شریک implementation یا advisor داده در بازار UK/آمریکای شمالی است که discovery و pilot را تسهیل می‌کند. مسیر Bold، evidence pack عمودی برای عملیات مالی یا خدمات حرفه‌ای است؛ این مسیر فقط پس از مشاهدهٔ wording و workflow مشترک در چند pilot اجرا شود.

Microsoft Purview، Alteryx و KNIME همگی governance/quality/lineage را در سطح platform عرضه می‌کنند.[2] [3] [4] بنابراین پیام growth DataSense باید بر replacement پلتفرم متمرکز نباشد؛ باید نشان دهد چگونه output تحلیلی desktop در کمتر از یک workflow به artifact قابل‌دفاع تبدیل می‌شود.

## تصمیم‌گیری پس از روز ۹۰

| حالت | evidence | تصمیم |
|---|---|---|
| Go | دو یا بیشتر pilot تکرارشونده، sponsor اقتصادی، blocker مشترک و proposal قابل‌قبول | verticalize message، بسته Team/Enterprise را تکمیل و sales-assisted motion بسازید. |
| Narrow | ارزش دیده می‌شود اما فقط در یک workflow/vertical | product و template را روی همان wedge متمرکز کنید. |
| Pivot | مسئله واقعی است اما evidence-first خریداری نمی‌شود | positioning را به integration/platform incumbent یا vertical outcome تغییر دهید. |
| Stop | adoption و sponsor هر دو ضعیف‌اند | سرمایه‌گذاری feature را متوقف و مسئله/segment جدید را از صفر discovery کنید. |

## منابع

[1]: https://www.evanta.com/resources/cdao/survey-report/top-3-priorities-for-cdaos-in-2025 "Evanta — Top 3 Priorities for CDAOs in 2025"
[2]: https://learn.microsoft.com/en-us/purview/data-governance-overview "Microsoft Learn — Data Governance with Microsoft Purview"
[3]: https://www.alteryx.com/ "Alteryx — Unified Data Analytics Platform"
[4]: https://www.knime.com/knime-for-enterprise "KNIME — For Enterprise"
