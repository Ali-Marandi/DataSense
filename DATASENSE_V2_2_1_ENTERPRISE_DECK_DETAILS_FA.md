# جزئیات دک سازمانی DataSense 2.2.1

## هدف، مخاطب و چارچوب ارائه

این دک ۱۲ اسلایدی برای مدیران ارشد، خریداران سازمانی، مالکان داده، تیم امنیت و compliance طراحی شده است. پیام مرکزی آن این است که DataSense 2.2.1 یک پایهٔ عملیاتی برای **Trusted Analytics** فراهم می‌کند و milestone بعدی سازمانی باید هویت متمرکز، RBAC، SAML SP-initiated و evidence قابل‌ممیزی را به‌صورت مرحله‌ای اضافه کند.

> اسلایدهای ۱ تا ۶ قابلیت‌ها و ارزش نسخهٔ desktop منتشرشده را بیان می‌کنند. اسلایدهای ۷ تا ۱۲ معماری هدف، کنترل‌پلین و تصمیم milestone بعدی هستند و نباید به‌عنوان قابلیت کاملِ فعال‌شده در desktop v2.2.1 معرفی شوند.

| صفحه | شناسه | عنوان | هدف و محتوای کلیدی | پیام گذار |
|---:|---|---|---|---|
| 1 | `cover` | DataSense 2.2.1 | عنوان، زیرعنوان Trusted Analytics و مسیر دسترسی سازمانی. | حرکت از چشم‌انداز به وضعیت انتشار. |
| 2 | `release_ready` | نسخهٔ ویندوز آمادهٔ استفاده | Setup، Portable ZIP، executable مستقل، release baseline و آمادگی Windows. | نصب‌پذیری کافی نیست؛ باید به داده اعتماد کرد. |
| 3 | `trust_center` | Trust Center و تحلیل قابل‌اعتماد | قرارداد داده، evidence JSON/UTC و کشف محلی PII. | Trust از قراردادهای قابل‌توضیح شروع می‌شود. |
| 4 | `data_contracts` | قرارداد داده و نتیجهٔ قابل‌توضیح | ruleهای null، unique، range، allowlist، regex و freshness؛ pass/fail/error. | severityها وزن یکسان ندارند. |
| 5 | `quality_score` | امتیاز کیفیت وزن‌دار | فرمول score، وزن critical/high/medium/low و جدایی score از gate. | evidence کیفیت به ارزش تجاری تبدیل می‌شود. |
| 6 | `commercial_value` | ارزش تجاری Trusted Analytics | کاهش ریسک تصمیم، بازتولیدپذیری و زبان مشترک audit. | برای مقیاس سازمانی، هویت و policy باید متمرکز شوند. |
| 7 | `control_plane` | Enterprise Control Plane | desktop public client، IdP، API مرکزی، organization/membership/audit و tenant isolation. | اجرای policy از نقش‌های server-side آغاز می‌شود. |
| 8 | `rbac` | RBAC و مجوزدهی قابل‌ممیزی | Owner/Admin/Data Steward/Analyst/Viewer/Auditor، deny-by-default و 404 cross-tenant. | principal امن با SSO ایجاد می‌شود. |
| 9 | `saml_sso` | SSO/SAML با امنیت پیش‌فرض | AuthnRequest، ACS strict، signature/audience/time/recipient/InResponseTo، PKCE و replay cache. | تحویل باید مرحله‌ای و evidence-driven باشد. |
| 10 | `roadmap` | مسیر تحویل پنج‌مرحله‌ای | Control Plane، RBAC، SAML SP، desktop binding و hardening. | success باید با test تعریف شود. |
| 11 | `success_metrics` | معیارهای موفقیت سازمانی | deny audit، rejection SAML، role refresh، evidence و آزمون‌های regression. | تصمیم اجرایی اکنون روشن است. |
| 12 | `decision` | تصمیم پیشنهادی | تثبیت 2.2.1، tenant پایلوت IdP و roadmap با owner/exit criteria. | دعوت به تخصیص مالک و شروع pilot. |

## داده‌ها و گزاره‌های قابل‌گفتن

| موضوع | عبارت مجاز در ارائه | مرز مهم |
|---|---|---|
| انتشار Windows | v2.2.1 با installer، portable و executable عرضه شده است. | شماره/نام asset را با صفحهٔ Release نهایی راستی‌آزمایی کنید. |
| آزمون | baseline انتشار ۷۰ آزمون موفق داشت؛ validation اخیر پس از اصلاح PyQt و Schema Drift Guard، ۷۹ آزمون موفق ثبت کرده است. | این دو عدد متعلق به زمان/دامنهٔ متفاوت‌اند و نباید با هم جایگزین شوند. |
| کیفیت | score وزنی است و Quality Gate policy مستقل دارد. | score به‌تنهایی تایید production نیست. |
| SAML/RBAC | reference implementation و unit test وجود دارد. | production هنوز نیازمند IdP staging، secret management، pentest و approval عملیاتی است. |
| انطباق | چک‌لیست SOC 2/ISO موجود است. | وجود چک‌لیست معادل اخذ certification نیست. |

## ساختار زمان‌بندی

مدت کل توصیه‌شده ۱۳ تا ۱۵ دقیقه به‌علاوهٔ پنج دقیقه پرسش‌وپاسخ است. پوشش اسلایدهای محصول نباید بیش از شش دقیقه طول بکشد تا برای architecture و تصمیم اجرایی زمان کافی باقی بماند. برای جلسهٔ executive کوتاه، اسلایدهای ۴ و ۵ را در یک دقیقه خلاصه کنید و اسلایدهای ۷، ۹، ۱۰ و ۱۲ را حفظ کنید.

## منابع همراه دک

اسکریپت کامل جمله‌به‌جمله، talking points، مدت هر اسلاید، انتقال‌ها و پاسخ پیشنهادی پرسش‌وپاسخ در فایل `DATASENSE_V2_2_1_PRESENTER_SCRIPT_FA.md` قرار دارد. Speaker notes متصل به پروژهٔ اسلاید نیز در `datasense_v221_enterprise_deck/slide_notes.md` موجود است. دک نهایی در نشانی `manus-slides://L0jbdMj6kzxN5XUGp4toKI` قابل‌نمایش است.
