# فرضیهٔ محصول و اعتبارسنجی تجاری DataSense

## وضعیت مبنا — ۱۴ اوت ۲۰۲۶

DataSense امروز یک نرم‌افزار Windows محلی-اول برای تحلیل‌گران داده است که ورود و آماده‌سازی داده، آمار، مدل‌سازی، نمودار و گزارش را بدون کدنویسی ترکیب می‌کند. تمایز عملیاتی موجود آن **Trust Center** است: اسکن محلی دادهٔ حساس، Data Contract، Quality Gate، Schema Drift، lineage metadata، گزارش ممیزی JSON و evidence قابل‌حمل. Control Plane سازمانی نیز دارای کد مرجع SAML/RBAC/JWT، tenant isolation، audit، quality-observation، outbox، metrics و manifestهای Kubernetes است؛ اما فعال‌سازی production آن مشروط به IdP sandbox، migration، acceptance evidence و approval عملیاتی است.

> مرز ادعا: Control Plane و worker نباید به‌عنوان سرویس production فعال فروخته شوند. محصول قابل‌استفادهٔ فعلی، desktop و قابلیت‌های Trust Center محلی است؛ معماری سازمانی مسیر عرضهٔ مرحله‌ای بعدی محسوب می‌شود.

## مسئلهٔ مشتری

تحلیل‌گران و تیم‌های داده در سازمان‌های حساس به داده میان دو گزینهٔ ناکامل قرار می‌گیرند: ابزار self-service سریع اما کم‌ممیزی، یا platform سازمانی پیچیده و پرهزینه که adoption آن زمان‌بر است. مسئلهٔ اصلی صرفاً «تحلیل داده» نیست؛ **تبدیل سریع تحلیل محلی به خروجی قابل‌دفاع در برابر مالک داده، تیم امنیت و ممیز** است.

## مشتری هدف اولیه — فرضیهٔ قابل‌آزمون

| جزء | تعریف فعلی | وضعیت اطمینان | روش اعتبارسنجی |
|---|---|---:|---|
| Beachhead پیشنهادی | تیم‌های تحلیل، BI و داده در سازمان‌های ۵۰ تا ۵۰۰۰ نفره با دادهٔ جدولی حساس و الزام evidence | متوسط | ۱۵ مصاحبهٔ مسئله‌محور و ۳ design partner در ۶۰ روز |
| کاربر اصلی | Data analyst / BI analyst که فایل یا extract را در Windows تحلیل می‌کند | بالا | مشاهدهٔ workflow و زمان-to-first-trusted-report |
| خریدار اقتصادی | Head of Data، مدیر BI، CISO/Compliance sponsor یا COO واحد عملیاتی | متوسط | discovery call با فرآیند خرید و budget owner |
| Job-to-be-done | «قبل از ارسال گزارش یا export، ثابت کن dataset و تحول‌های مهم قابل‌اعتماد و قابل‌ردیابی‌اند.» | متوسط تا بالا | سنجش قبل/بعد زمان تهیهٔ evidence و defect escape |
| ضد مشتری اولیه | سازمانی که فقط dashboard cloud می‌خواهد یا به deployment مرکزی کامل از روز اول نیاز دارد | بالا | qualification در اولین تماس فروش |

## ارزش پیشنهادی و جایگاه

**جایگاه پیشنهادی:** «لایهٔ اعتماد محلی-اول برای تحلیل دادهٔ سازمانی؛ از فایل خام تا evidence قابل‌ممیزی، بدون مجبورکردن تحلیل‌گر به ساخت pipeline یا انتقال داده به cloud.»

ارزش پیشنهادی در نخستین پنج دقیقه باید قابل‌مشاهده باشد: کاربر dataset را باز می‌کند، PII و quality risk را می‌بیند، Contract پیشنهادی را بازبینی می‌کند و audit JSON صادر می‌نماید. ارزش اقتصادی مورد ادعا باید در پایلوت اندازه‌گیری شود: کاهش زمان triage، کاهش خطای داده پیش از report، و کاهش زمان آماده‌سازی evidence. تا پیش از اندازه‌گیری، این موارد **فرضیه** هستند، نه ادعای ROI.

## مزیت رقابتی قابل‌ساخت

| لایهٔ مزیت | دارایی یا تصمیم | اثر | معیار دفاع‌پذیری |
|---|---|---|---|
| محصول | Trust Center در لحظهٔ تحلیل، نه صرفاً پس از ingest | مسیر کاربر کوتاه‌تر برای evidence | زمان از import تا audit export |
| داده/اعتماد | evidence metadata-only، schema fingerprint، contract و audit trail | قابلیت review بدون انتقال valueهای خام | پوشش policy و نرخ evidence کامل |
| معماری | local-first desktop با مسیر Control Plane اختیاری | مناسب برای محیط‌های حساس/کم‌اعتماد به cloud | پایلوت‌های بدون egress دادهٔ خام |
| توزیع | integration با workflow فعلی Excel/CSV/SQL و Windows | اصطکاک adoption کمتر از مهاجرت platform | activation و retention cohort |
| switching cost مشروع | policy، contract، audit history و templateهای domain مشتری | هزینهٔ ترک بر پایهٔ ارزش انباشته، نه lock-in مصنوعی | contract reuse و template adoption |

## اولویت‌بندی سرمایه‌گذاری محصول

| سبد | تصمیم | دلیل تجاری | شرط آغاز یا شرط توقف |
|---|---|---|---|
| **Now** | Signed Evidence Bundle و Desktop SSO binding با IdP sandbox | شکاف مستقیم در فروش سازمانی و پرسش‌های امنیتی | فقط با یک design partner و owner امنیتی مشخص |
| **Now** | Pilot instrumentation: activation، evidence export، blocked-run reason، time-to-first-value | بدون دادهٔ رفتار، قیمت‌گذاری و PMF حدس است | telemetry metadata-only و opt-in/policy روشن |
| **Next** | Column lineage graph و workflow runner محدود | افزایش retention و ارزش تیمی | پس از اثبات استفادهٔ تکراری Contract/Gate |
| **Later** | catalog، policy-as-code و connector marketplace | platform/economy مؤثر اما پرهزینه | پس از تعریف ownership model و حداقل سه design partner |
| **Maybe** | anomaly detection مبتنی بر AI | فقط در صورت وجود baseline/owner/false-positive loop | اگر کیفیت baseline کافی نبود، شروع نشود |
| **Do Not Do** | cloud dashboard عمومی، marketplace باز، یا ادعای certification پیش از evidence | تمرکز را می‌شکند و ریسک امنیتی/حقوقی می‌سازد | رد در review roadmap |

## فرضیه‌های قابل‌آزمون ۶۰ روزه

| کد | فرضیه | شاخص موفقیت | معیار شکست/تصمیم |
|---|---|---|---|
| H1 | تحلیل‌گر ارزش اولیه را در کمتر از ۵ دقیقه از Trust Center می‌گیرد. | حداقل ۷۰٪ کاربران پایلوت یک Contract را بازبینی و report صادر کنند. | کمتر از ۴۰٪؛ onboarding یا مسئلهٔ هدف بازطراحی شود. |
| H2 | evidence قابل‌حمل دلیل قابل‌پرداخت برای تیم‌های حساس به داده است. | ۲ از ۳ design partner sponsor اقتصادی معرفی کنند. | sponsor یا budget owner پیدا نشود؛ positioning تغییر کند. |
| H3 | SSO و signed evidence blockers اصلی فروش Enterprise هستند. | پرسش‌نامهٔ امنیتی یا RFP آن‌ها را critical بداند. | blocker اصلی integration/collaboration باشد؛ ترتیب roadmap بازبینی شود. |
| H4 | local-first برتری واقعی در بازار هدف است. | مشتری اصرار کند دادهٔ خام از desktop خارج نشود یا private deployment بخواهد. | cloud-first پذیرفته شود؛ SaaS companion دوباره ارزیابی شود. |

## North Star و KPIهای اولیه

**North Star Metric:** تعداد «Trusted Analysis Runs» هفتگی؛ یعنی اجرای تحلیل یا export که Contract/Gate معتبر و evidence قابل‌صادرات دارد. این معیار باید همراه با کیفیت outcome دیده شود، نه صرفاً تعداد click.

| مرحلهٔ قیف | KPI | تعریف |
|---|---|---|
| Acquisition | Qualified pilot applications | سازمانی با owner، دادهٔ نمونه و مسئلهٔ مستند |
| Activation | Time to First Trusted Report | زمان از import تا audit/report صادرشده |
| Engagement | Weekly Trusted Analysis Runs | runهای معتبر در هر workspace/سازمان |
| Retention | Contract reuse rate | سهم runهایی که از Contract موجود استفاده می‌کنند |
| Revenue | Pilot-to-paid conversion | پایلوت‌هایی که به قرارداد پولی تبدیل می‌شوند |
| Trust | Evidence completion rate | runهایی که contract، gate، fingerprint و audit metadata دارند |

## Immediate Next Actions

گام بعدی، تحقیق به‌روز و مبتنی بر منبع دربارهٔ بازار Data Observability / Data Quality / Analytics Governance، رقبای مستقیم و غیرمستقیم، و انتخاب market beachhead است. سپس بسته‌بندی و قیمت‌گذاری فقط با فرضیات صریح و سه سناریوی قابل‌ویرایش طراحی می‌شود. اجرای فنی باید با Signed Evidence Bundle یا Desktop SSO شروع شود، اما تنها پس از اینکه design-partner interview ثابت کند کدام‌یک blocker فروش واقعی است.

## منابع داخلی

- `README.md` — قابلیت‌های قابل‌عرضهٔ desktop.
- `ENTERPRISE_PRODUCT_EVOLUTION_FA.md` — اولویت‌ها، Done criteria و اصول جهانی‌سازی.
- `ENTERPRISE_ROADMAP_FA.md` — vision، بسته‌بندی اولیه و مرزبندی عرضه.
- `DATASENSE_V2_2_1_ENTERPRISE_QA_AND_OBJECTIONS_FA.md` — مرز ادعاهای enterprise و پاسخ به اعتراض‌ها.
