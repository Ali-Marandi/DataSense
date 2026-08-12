# مبانی پژوهشی milestone دسترسی سازمانی

## RBAC

مدل مرجع NIST، عناصر کاربران، نقش‌ها، مجوزها، عملیات و اشیاء را از هم جدا می‌کند. رابطهٔ کاربر–نقش و نقش–مجوز بسیاری‌به‌بسیاری است. این مدل مبنای طراحی DataSense خواهد بود: هر عضویت سازمانی مجموعه‌ای از نقش‌ها دارد؛ نقش‌ها اجازهٔ انجام actionهای مشخص روی منابعی مانند پروژه، dataset، قرارداد کیفیت و گزارش ممیزی را تعیین می‌کنند. نقش‌های سلسله‌مراتبی، تفکیک وظایف و محدودیت سطح داده به‌عنوان گسترش‌های کنترل‌شده اضافه می‌شوند.

منبع: https://csrc.nist.gov/projects/role-based-access-control

## SSO/SAML

DataSense باید ابتدا جریان SP-initiated Web Browser SSO را پیاده کند. برنامه AuthnRequest دارای شناسهٔ یکتا تولید می‌کند، کاربر را به IdP هدایت می‌کند و ACS فقط Response امضاشده‌ای را می‌پذیرد که `InResponseTo` آن با درخواست ذخیره‌شده، `Audience` آن با entity ID سرویس، `Recipient` آن با ACS URL و بازهٔ زمانی آن با clock skew مجاز تطبیق دارد. نگاشت NameID و attributeها به membership سازمانی و نقش‌ها مستقل از assertion ذخیره می‌شود. جلسهٔ محلی کوتاه‌عمر است و logout، rotation گواهی و گزارش ممیزی دارد.

کنترل‌های اجباری: TLS، اعتبارسنجی XML schema با نسخهٔ محلی و سخت‌شده، validation امضای XML با کلیدهای pinned از metadata مورداعتماد، رد assertionهای تکراری با replay cache، رد مقصد/audience/issuer ناسازگار، TTL کوتاه، و جداسازی کلید امضا از رمزنگاری. IdP-initiated SSO در نسخهٔ اول فعال نمی‌شود مگر با کنترل‌های ضد replay و allowlist دقیق RelayState.

منابع:
- https://docs.oasis-open.org/security/saml/v2.0/saml-profiles-2.0-os.pdf
- https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet.html

## نکتهٔ ارائه

جست‌وجوی تصویر مرجع عمومی برای استفاده در اسلایدها نتیجهٔ معتبر نداد. برای جلوگیری از مسئلهٔ حق‌نشر و کمبود کیفیت، ارائه بر پایهٔ نمودارهای معماری و بصری‌سازی‌های اختصاصی تولید می‌شود.

## SOC 2، ISO 27001 و federation

SOC 2 بر معیارهای Trust Services شامل Security، Availability، Processing Integrity، Confidentiality و Privacy تکیه دارد. برای DataSense، چک‌لیست باید کنترل‌های هویت، منطق مجوز، تغییرات policy، logging، کنترل تغییر، پاسخ به رخداد، مدیریت کلید، پشتیبان‌گیری و شواهد کیفیت داده را به این معیارها نگاشت کند.

ISO/IEC 27001:2022 الزام‌های یک ISMS را تعریف می‌کند و مدیریت ریسک، محرمانگی، یکپارچگی و دسترس‌پذیری را به سیاست، افراد و فناوری متصل می‌کند. بنابراین چک‌لیست فقط یک فهرست تنظیم فنی نیست؛ باید مالک کنترل، شواهد، تناوب بازبینی و وضعیت ریسک داشته باشد.

NIST SP 800-63C قدیمی‌تر است و صفحهٔ NIST به SP 800-63-4 به‌عنوان مرجع جاری اشاره می‌کند. با این وجود، متن federation آن برای طراحی مفید است: IdP احراز هویت را انجام می‌دهد و RP assertion را برای شناسایی و تصمیم مجوز استفاده می‌کند. در پیاده‌سازی باید IdP allowlist، حداقل attribute، حفاظت assertion و تفکیک authentication از authorization رعایت شود.

منابع:
- https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022
- https://www.iso.org/standard/27001
- https://pages.nist.gov/800-63-3/sp800-63c.html

## Data Observability و Schema Drift

Schema drift تغییر غیرمنتظره یا ناخواسته در ساختار داده، مانند افزودن/حذف ستون یا تغییر نوع داده است و اگر رهگیری نشود می‌تواند به ناهماهنگی، شکست برنامه و گزارش نادرست منجر شود. راهکار عملی برای DataSense، snapshot نسخه‌دار schema، مقایسهٔ deterministic و policy سازگاری است.

Data contract صرفاً schema نیست و می‌تواند structure، integrity constraints، metadata، policy و تکامل/نسخه‌بندی را پوشش دهد. این یافته مبنای افزودن Schema Drift Guard به Trust Center است: تغییرهای additive در حالت permissive قابل‌قبول یا قابل‌هشدارند؛ حذف ستون، تغییر نوع و تغییر nullability با توجه به policy block می‌شوند.

منابع:
- https://docs.confluent.io/cloud/current/sr/fundamentals/data-contracts.html
- https://www.acceldata.io/blog/schema-drift
- https://montecarlo.ai/blog-data-contracts-explained
