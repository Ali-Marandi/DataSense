# نقشهٔ توسعهٔ تجاری و جهانی‌سازی DataSense

## تصمیم محصول در این iteration

قابلیت **Schema Drift Guard** به Trust Center اضافه و آزمایش شده است. این قابلیت baseline ساختار داده را بدون ذخیرهٔ مقدار یا نمونهٔ داده ثبت می‌کند، تغییرهای ستون/dtype/nullability/order را تشخیص می‌دهد، آن‌ها را با policy سازگاری مقایسه می‌کند و نتیجهٔ `compatible`، `blocked` یا `not configured` تولید می‌نماید. baseline، policy و report در `.dsproj` و audit export پایدار می‌شوند. این قابلیت حلقهٔ مفقوده میان data contract و تغییر کنترل‌نشدهٔ upstream را می‌بندد.

Schema drift در عمل شامل تغییرهای غیرمنتظره در ساختار مانند افزودن، حذف یا تغییر نوع ستون است و می‌تواند به ناسازگاری و اختلال downstream منجر شود.[1] الگوی data contract بالغ نیز structure، integrity constraints، metadata، policy و evolution/versioning را همراه می‌بیند.[2] پیاده‌سازی DataSense با همین مرزبندی طراحی شده است: snapshot فقط metadata دارد؛ policy تعیین می‌کند کدام تغییر قابل‌قبول است؛ و status جایگزین تصمیم مالک داده نمی‌شود.

| قابلیت اجراشده | ارزش تجاری | وضعیت |
|---|---|---|
| Quality Gate + trend history | تبدیل rule result به تصمیم release قابل‌توضیح و نمایش روند کیفیت. | اجرا و آزمون شده |
| Schema Drift Guard | تشخیص breaking change پیش از اتکا به تحلیل یا export. | اجرا و آزمون شده |
| Headless PyQt test bootstrap | اجرای پایدار ۷۷ آزمون در CI/sandbox بدون X server. | اجرا و آزمون شده |
| Control Plane reference implementation | پایهٔ SAML/RBAC چندسازمانی با audit و tenant isolation. | کد مرجع و test unit آماده؛ نیازمند staging IdP برای production |

## قابلیت‌های اولویت‌دار بعدی

| اولویت | قابلیت | مشتری/مسئله | تعریف Done عملیاتی |
|---:|---|---|---|
| P0 | Desktop SSO binding | ورود سازمانی امن بدون نگهداری credential در برنامه. | browser flow، PKCE، credential-store سیستم‌عامل، offline/error UX و integration test با IdP sandbox. |
| P0 | Signed evidence bundle | ممیز و مشتری نیاز دارند بدانند report پس از تولید تغییر نکرده است. | canonical JSON، HMAC/KMS signature، key id، verify command و immutable audit event. |
| P1 | Column lineage graph | analyst و auditor باید بدانند هر ستون از کدام transform آمده است. | DAG تغییرات، input/output schema، author/time، export JSON و view در Trust Center. |
| P1 | Anomaly monitoring | ruleهای قطعی، تغییرهای آماری ناگهانی را پوشش نمی‌دهند. | baseline robust، threshold قابل‌تنظیم، explainability، false-positive feedback و PII-safe evidence. |
| P1 | Contract scheduler/runner | کنترل کیفیت باید پیش از export و در اجرای دوره‌ای نیز انجام شود. | schedule local/Control Plane، notification، retry، history، concurrency policy و runbook. |
| P1 | Parquet evidence metadata | فایل‌های تحویلی باید policy و quality context داشته باشند. | metadata شامل contract version، score، gate، schema fingerprint و export event id. |
| P2 | Data catalog and ownership | مقیاس enterprise با مالک نامشخص و datasetهای ناشناخته شکست می‌خورد. | owner، steward، classification، retention، discovery و approval workflow. |
| P2 | Policy-as-code | policyهای کیفیت، export و access باید reviewable و versioned باشند. | Git-backed policy bundle، PR approval، evaluation API، dry-run و rollback. |
| P2 | Governed connector marketplace | اتصال به warehouse/SaaS بدون گسترش uncontrolled data egress. | connector manifest، scope review، secret manager، DLP policy، audit و kill switch. |

## جهانی‌سازی واقعی محصول

جهانی‌سازی فقط ترجمهٔ labelها نیست. محصول باید روی زبان، منطقه، مقررات، عملیات و فروش بین‌المللی آماده باشد.

| محور | اقدام اجرایی | معیار پذیرش |
|---|---|---|
| i18n و RTL | انتقال متن‌های UI به catalog، locale-aware format تاریخ/عدد، layout RTL برای فارسی/عربی و fallback زبان. | تست snapshot برای `en` و `fa`، عدم hard-code متن در widgetها. |
| منطقه و data residency | انتخاب region، tag residency روی organization/dataset، منع export خلاف policy و retention محلی. | policy test برای transfer منع‌شده و audit record region. |
| زمان و تقویم | ذخیرهٔ UTC، نمایش برحسب timezone سازمان، validation timestamp بدون ambiguity. | تست DST/timezone و evidence UTC. |
| حریم خصوصی بین‌المللی | classification، DSR workflow، retention و legal-hold به‌صورت policy. | register داده، approval evidence و deletion/hold test. |
| پایداری عملیاتی | multi-region Control Plane، DR، SLO، localization support و status page. | restore exercise، SLO dashboard و incident drill. |
| فروش سازمانی | deployment guide، security questionnaire pack، SOC 2/ISO mapping، SBOM و release provenance. | data room نسخه‌دار و پاسخ‌گویی قابل‌ردیابی به RFP. |

## مسیر عرضهٔ پیشنهادشده

در ۹۰ روز اول، تمرکز باید روی یک پایلوت کنترل‌شده باشد، نه افزودن هم‌زمان همهٔ قابلیت‌ها. ابتدا دو dataset حساس و یک سازمان پایلوت انتخاب می‌شوند. Quality Gate، Schema Drift و evidence export روی آن‌ها فعال می‌گردند. هم‌زمان یک IdP sandbox برای SAML/RBAC تکمیل می‌شود. پس از اثبات acceptance criteria، Signed Evidence Bundle و desktop SSO binding وارد release بعدی می‌شوند. قابلیت‌های lineage و anomaly monitoring تنها زمانی شروع شوند که owner، baseline و راهبرد پاسخ به alert از پیش تعیین شده باشد.

> اصل راهنما: هر قابلیت enterprise باید یک policy، یک owner، یک evidence trail، یک روش آزمون و یک مسیر rollback داشته باشد؛ در غیر این صورت فقط یک feature UI است، نه یک کنترل تجاری قابل‌فروش.

## منابع

[1]: https://www.acceldata.io/blog/schema-drift "Schema Drift — structural change detection and mitigation"
[2]: https://docs.confluent.io/cloud/current/sr/fundamentals/data-contracts.html "Data Contracts for Schema Registry — structure, integrity, metadata, policies and evolution"
[3]: https://montecarlo.ai/blog-data-contracts-explained "Data Contracts 101 — ownership, versioning and enforcement"
