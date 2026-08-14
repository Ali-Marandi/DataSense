# Q&A و پاسخ به اعتراض‌های سازمانی — DataSense v2.2.1

## قاعدهٔ ارائه

در پاسخ به پرسش‌های سازمانی، مرز میان قابلیت فعال در desktop v2.2.1، reference implementation Control Plane و معماری هدف Kubernetes باید حفظ شود. پاسخ حرفه‌ای نباید roadmap را به‌عنوان قابلیت production معرفی کند. پاسخ‌دهنده ابتدا مسئله را تأیید می‌کند، سپس شاهد فعلی را بیان می‌نماید و در پایان action یا شرط پذیرش بعدی را مشخص می‌کند.

> جملهٔ مرجع: «v2.2.1 و Trust Center پایهٔ عملیاتی موجودند؛ Control Plane، outbox worker، SAML staging و Kubernetes مسیر تحویل سازمانی هستند که برای production به migration، محیط آزمایش، acceptance evidence و approval نیاز دارند.»

## پرسش‌های کلیدی مدیران

| پرسش یا اعتراض | پاسخ پیشنهادی گفتاری | شاهد یا اقدام بعدی | اسلاید ارجاع |
|---|---|---|---:|
| «آیا محصول واقعاً production-ready است یا صرفاً prototype؟» | «نسخهٔ Windows v2.2.1 و Trust Center یک baseline عملیاتی‌اند و suite فعلی ۸۲ آزمون موفق دارد. اما قابلیت‌هایی مانند Control Plane، worker و Kubernetes را production-active معرفی نمی‌کنیم؛ آن‌ها با manifest، schema، hook و acceptance plan آمادهٔ milestone بعدی‌اند.» | Release assets، گزارش pytest و roadmap/exit criteria. | ۲، ۱۰، ۱۱ |
| «آیا SOC 2 یا ISO 27001 دارید؟» | «کنترل‌ها و checklistهای هم‌راستا تهیه شده‌اند، اما certification ادعا نمی‌کنیم. certification نتیجهٔ scope، شواهد عملیاتی و ارزیابی مستقل است. هدف ما ساخت evidence قابل‌ممیزی برای آماده‌سازی آن مسیر است.» | SOC2/ISO checklist و تعیین owner انطباق. | ۳، ۶، ۱۲ |
| «دادهٔ حساس به بیرون می‌رود؟» | «Trust Center در desktop findingهای PII را به‌صورت metadata ثبت می‌کند و schema/lineage value خام نگه نمی‌دارند. telemetry مرکزی نیز باید metadata-only، authenticated و کم‌کاردینال باشد. قبل از هر integration، data classification و policy مشتری تعیین می‌شود.» | PII scan، audit export، data-flow review. | ۳، ۴ |
| «چرا یک Quality Score کافی نیست؟» | «Score فقط وزن evidence است؛ Gate policy کنترل تصمیم است. ممکن است score بالا باشد ولی یک critical failure action حساس را block کند. این تفکیک از acceptance ظاهراً خوب اما پرریسک جلوگیری می‌کند.» | Gate policy، quality report و blocked-run evidence. | ۵ |
| «false positive Gate کسب‌وکار را متوقف نمی‌کند؟» | «Gate قابل‌نسخه‌بندی و policy-driven است. قبل از hard enforcement، profile مناسب و stage rollout تعریف می‌شود. override فقط با permission، TTL، دلیل و audit مجاز است؛ silent bypass راه‌حل نیست.» | auto-blocking guide، override workflow، trend/history. | ۵، ۱۰ |
| «آیا SAML/SSO فقط روی اسلاید است؟» | «کد reference برای SP-initiated SAML، PKCE، validation و replay prevention وجود دارد و security-flow test دارد. اما اتصال به IdP مشتری و production rollout منوط به sandbox، key management و negative testهای واقعی است.» | IdP staging checklist و SAML test evidence. | ۷، ۹، ۱۰ |
| «RBAC را با پنهان‌کردن دکمه پیاده می‌کنید؟» | «خیر. UI صرفاً تجربهٔ کاربر است؛ permission و tenant boundary باید server-side و deny-by-default باشد. test cross-tenant access باید 404/audit ثبت کند.» | RBAC middleware و security-flow tests. | ۷، ۸، ۱۱ |
| «اگر notification provider قطع شود چه می‌کنید؟» | «API نباید منتظر provider بماند. event در outbox transaction ثبت می‌شود؛ worker جداگانه با retry، lease recovery و DLQ آن را پردازش می‌کند. provider outage به backlog/oldest age alert تبدیل می‌شود، نه data loss.» | outbox schema، worker tests، Prometheus rules. | ۷، ۱۰، ۱۱ |
| «چه تضمینی برای exactly-once notification دارید؟» | «در distributed delivery، delivery واقعی at-least-once است؛ ما deduplication با idempotency key و state transition اتمی طراحی می‌کنیم. provider باید Idempotency-Key را پشتیبانی کند و duplicate را بدون side effect قبول کند.» | fake-sink acceptance و provider contract. | ۷، ۱۰ |
| «چگونه متوجه می‌شوید queue عقب افتاده است؟» | «pending depth، oldest pending age، dead events و lease recovery metrics صادر می‌شود. Grafana/Prometheus rule برای backlog، age، DLQ و recovery loop وجود دارد. آستانه‌ها قبل از paging با baseline مشتری کالیبره می‌شوند.» | dashboard، alert rules و load/soak plan. | ۱۰، ۱۱ |
| «این معماری چقدر بار را تحمل می‌کند؟» | «ادعای throughput بدون workload مشتری نمی‌کنیم. برنامهٔ acceptance/load شامل baseline، steady، burst، soak و fault scenario است. HPA API و scaling worker باید بر مبنای SLO و metrics واقعی تنظیم شوند.» | Locust plan، HPA و release gate. | ۱۰، ۱۱ |
| «چرا Kubernetes؟ آیا هزینه و پیچیدگی را زیاد نمی‌کند؟» | «Kubernetes برای tenantهای نیازمند HA، worker مستقل، policy شبکه و monitoring متمرکز یک گزینه است، نه پیش‌نیاز desktop. برای پایلوت می‌توان Control Plane را در محیط staging محدود اجرا کرد؛ انتخاب platform بر اساس حجم، SLO و مالکیت عملیات انجام می‌شود.» | option comparison و architecture decision record. | ۷، ۱۰ |
| «vendor lock-in چیست؟» | «contractها، evidence JSON، schema fingerprint و lineage metadata portable هستند. SAML بر استاندارد federation و APIها بر HTTP/JWT متکی‌اند. برای هر integration، export و exit path باید در قرارداد مشتری ثبت شود.» | export JSON و integration specification. | ۴، ۹ |
| «چرا اکنون بخریم و منتظر milestone سازمانی نمانیم؟» | «v2.2.1 هم‌اکنون ارزش Trust Center و evidence را در Windows ایجاد می‌کند. پایلوت امروز داده و policy واقعی لازم برای طراحی دقیق milestone سازمانی را تولید می‌کند؛ بدون آن، enterprise design صرفاً فرضی می‌ماند.» | pilot success criteria و tenant selection. | ۲، ۳، ۱۲ |

## سناریوی اعتراض امنیتی سخت

**مشتری می‌گوید:** «ما اجازه نمی‌دهیم desktop مستقیماً به سیستم‌های حساس وصل شود.»

**پاسخ پیشنهادی:** «این نگرانی درست است. الگوی پیشنهادی ما desktop را public client می‌داند و credential حساس را در آن قرار نمی‌دهد. هویت و policy در Control Plane مرکزی اعمال، eventها metadata-only و با RBAC ثبت می‌شوند. برای integration حساس، مسیر شبکه، secret manager، service account و audit scope در محیط staging مشتری بازبینی می‌شود. تا زمانی که این controls و acceptance tests پاس نشده‌اند، integration را production-ready اعلام نمی‌کنیم.»

**گذار:** «اگر موافق باشید، در مرحلهٔ بعد architecture workshop کوتاه برگزار می‌کنیم تا data flow، IdP، egress و evidence موردنیاز شما را به‌صورت مشخص طراحی کنیم.»

## سناریوی اعتراض مالی

**مشتری می‌گوید:** «ROI عددی شما کجاست؟»

**پاسخ پیشنهادی:** «بدون baseline مشتری، عدد صرفه‌جویی قطعی نمی‌دهیم. فرض قابل‌آزمون ما این است که قراردادهای قابل‌تکرار، defectهای داده را پیش از گزارش مدیریتی آشکار می‌کنند و evidence زمان audit را کاهش می‌دهد. در پایلوت، baseline شامل زمان triage، تعداد incident کیفیت، زمان تهیه evidence و نرخ blocked run تعریف می‌شود. سپس ROI با دادهٔ خود مشتری محاسبه می‌گردد.»

## سناریوی اعتراض عملیات

**مشتری می‌گوید:** «اگر worker crash کند یا پیام دوبار ارسال شود چه می‌شود؟»

**پاسخ پیشنهادی:** «worker claim را با lease می‌گیرد. اگر crash کند، lease منقضی و recovery event را دوباره pending می‌کند. delivery retry می‌شود و provider Idempotency-Key را دریافت می‌کند تا side effect تکراری کنترل شود. اگر retry budget تمام یا failure permanent باشد، event به DLQ می‌رود و redrive فقط با ticket و audit انجام می‌شود.»

## سناریوی اعتراض کیفیت

**مشتری می‌گوید:** «Gate مانع delivery فوری می‌شود.»

**پاسخ پیشنهادی:** «Gate بر اساس tier داده تنظیم می‌شود. محیط sandbox ممکن است فقط observe کند؛ tier حساس می‌تواند block کند. policy از score جداست و با contract owner تعیین می‌شود. برای exception واقعی، override محدود، زمان‌دار و قابل‌ممیزی وجود دارد. هدف حذف سرعت نیست؛ هدف جلوگیری از انتشار داده‌ای است که خودمان نمی‌توانیم از آن دفاع کنیم.»

## پاسخ‌های کوتاه برای Q&A سریع

| سؤال کوتاه | پاسخ ۲۰ ثانیه‌ای |
|---|---|
| «آیا داده را پاک می‌کنید؟» | «خیر. Trust Center evidence تولید می‌کند؛ remediation و publish تصمیم کنترل‌شدهٔ مالک داده است.» |
| «آیا score پایین یعنی داده حذف می‌شود؟» | «خیر. score پایین evidence است؛ Gate policy تعیین می‌کند کدام action باید hold شود.» |
| «آیا Schema Drift دادهٔ خام را ذخیره می‌کند؟» | «خیر. فقط schema metadata و fingerprint نگه می‌دارد، نه cell value یا sample.» |
| «آیا worker اکنون در production فعال است؟» | «خیر. worker code/schema/hook آماده شده، اما activation به migration، fake-sink acceptance و operations approval وابسته است.» |
| «آیا ۸۲ تست یعنی penetration test انجام شده؟» | «خیر. ۸۲ تست regression/logic هستند. penetration test یک فعالیت مستقل با scope و گزارش جداست.» |
| «گام بعدی چیست؟» | «انتخاب tenant پایلوت، owner business/security، محیط IdP staging و acceptance criteria.» |

## منابع داخلی برای پاسخ‌دهنده

پاسخ‌دهنده پیش از جلسه باید `DATASENSE_V2_2_1_PRESENTER_SCRIPT_FA.md`، `ENTERPRISE_CONTROL_PLANE_AND_LOAD_TEST_TALK_TRACK_FA.md`، `OUTBOX_WORKER_RECOVERY_AND_ERROR_HANDLING_GUIDE_FA.md`، `KUBERNETES_CICD_PIPELINE_GUIDE_FA.md` و گزارش آزمون جاری را مرور کند. در پاسخ‌های فنی، از وعدهٔ زمان‌بندی یا certification بدون تایید رسمی اجتناب کنید.
