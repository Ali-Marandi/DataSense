# چک‌لیست ممیزی امنیت و انطباق سازمانی DataSense

**نسخه:** 1.0  
**مالک پیشنهادی:** مدیر امنیت اطلاعات (CISO) و مالک محصول DataSense  
**دامنه:** نرم‌افزار Desktop، بستهٔ Windows، pipeline انتشار، Trust Center، Control Plane سازمانی، دادهٔ پشتیبان و تأمین‌کنندگان وابسته  
**وضعیت:** baseline اجرایی برای gap assessment؛ این سند به‌تنهایی گواهی SOC 2 یا ISO/IEC 27001 ایجاد نمی‌کند.

## نحوهٔ استفاده

ISO/IEC 27001:2022 برای ایجاد، استقرار، نگهداری و بهبود مستمر ISMS و مدیریت ریسک‌های اطلاعاتی طراحی شده است.[1] SOC 2 نیز معیارهای اعتماد شامل امنیت، دسترس‌پذیری، یکپارچگی پردازش، محرمانگی و حریم خصوصی را برای ارزیابی کنترل‌ها به‌کار می‌گیرد.[2] بنابراین هر سطر این سند باید به‌صورت یک control قابل‌آزمون اجرا شود: یک **مالک**، یک **شاهد تاریخ‌دار**، تناوب بازبینی و نتیجهٔ Pass/Partial/Fail داشته باشد.

> «Conformity with ISO/IEC 27001 means that an organization or business has put in place a system to manage risks related to the security of data owned or handled by the company.» — ISO [1]

برای SSO، IdP مسئول احراز هویت است و RP از assertion برای شناسایی و تصمیم مجوز استفاده می‌کند؛ این دو تصمیم نباید در یک attribute غیرمعتبر یا UI کلاینت ادغام شوند.[3] کنترل‌پلین پیشنهادی DataSense دقیقاً با همین تفکیک طراحی شده است.

| وضعیت پیشنهادی | معنا | اقدام ممیز |
|---|---|---|
| Pass | کنترل طراحی و اجرا شده و شواهد دورهٔ موردنظر کامل است. | نمونه‌گیری و ثبت شاهد. |
| Partial | کنترل وجود دارد، اما پوشش، تناوب یا شاهد ناقص است. | ایجاد remediation با مالک و موعد. |
| Fail | کنترل غایب، دور زده‌شده یا ناکارآمد است. | ثبت ریسک، کنترل جبرانی و escalation. |
| N/A | خارج از دامنه است و توجیه کتبی دارد. | تصویب مالک ریسک لازم است. |

## ۱. حاکمیت، ریسک و سیاست‌ها

این بخش به SOC 2 CC1، CC2، CC3 و CC5 و بندهای 4 تا 10 ISO/IEC 27001 مرتبط است. مالک محصول باید فهرست دارایی‌ها، مرز سرویس، و مسیرهای داده را حداقل سالانه و هنگام تغییر عمده بازبینی کند.

| شناسه | کنترل و نگاشت | پیاده‌سازی مورد انتظار در DataSense | شاهد قابل‌قبول | مالک / تناوب |
|---|---|---|---|---|
| GOV-01 | SOC 2 CC1.1, ISO 5.2 | سیاست امنیت، privacy، SDLC و استفادهٔ قابل‌قبول مصوب و نسخه‌دار باشد. | PDF/مخزن policy با تصویب و تاریخ بازبینی. | CISO / سالانه |
| GOV-02 | SOC 2 CC2.1, ISO 7.4 | کانال گزارش رخداد، vulnerability و درخواست داده تعریف و به مشتری اعلام شود. | صفحهٔ Trust Center، ticket نمونه و SLA پاسخ. | Security / فصلی |
| GOV-03 | SOC 2 CC3.1–CC3.4, ISO 6.1 | risk register شامل دارایی، تهدید، احتمال، اثر، کنترل و پذیرش ریسک نگهداری شود. | risk register و minutes کمیتهٔ ریسک. | CISO / فصلی |
| GOV-04 | SOC 2 CC5.1–CC5.3, ISO 5.3 | RACI برای release، SSO، RBAC، کیفیت داده و incident مشخص باشد. | ماتریس RACI و نمونهٔ approval. | Product/Security / شش‌ماهه |
| GOV-05 | ISO 5.9, 5.12, 5.13 | asset inventory شامل repo، runner CI، signing key، installer، Control Plane، PostgreSQL و Redis باشد. | CMDB/asset register و مالک هر دارایی. | IT/Security / ماهانه |
| GOV-06 | SOC 2 CC4.1, ISO 9.1 | KPI کنترل‌ها شامل patch SLA، MFA coverage، زمان revoke، failure rate Gate و backup restore success اندازه‌گیری شود. | داشبورد و trend سه ماه اخیر. | CISO / ماهانه |
| GOV-07 | ISO 7.5, 10.1 | استثناهای کنترل دارای ticket، ریسک، کنترل جبرانی، تاریخ انقضا و approval باشند. | exception register و نمونهٔ بسته‌شده. | Risk owner / ماهانه |

## ۲. هویت، SSO و RBAC

این بخش به SOC 2 CC6 و کنترل‌های identity/access در Annex A ISO 27001:2022 نگاشت می‌شود. در پیاده‌سازی فعلی، `organizations`، `identities`، `memberships`، `roles` و `permissions` منبع مجوز هستند؛ نقش یا گروه IdP فقط با provisioning و approval صریح وارد این مدل می‌شود.

| شناسه | کنترل و نگاشت | پیاده‌سازی مورد انتظار در DataSense | شاهد قابل‌قبول | مالک / تناوب |
|---|---|---|---|---|
| IAM-01 | SOC 2 CC6.1, ISO 5.15 | ماتریس حداقل‌دسترسی برای Owner، Admin، Data Steward، Analyst، Viewer و Auditor مصوب باشد. | role-permission matrix و pull request تغییر نقش. | Security/Product / شش‌ماهه |
| IAM-02 | SOC 2 CC6.2, ISO 5.16/5.18 | lifecycle هویت شامل joiner/mover/leaver و revoke فوری عضویت غیرفعال باشد. | ticket نمونهٔ offboarding و audit event revoke. | IT/HR / ماهانه نمونه‌گیری |
| IAM-03 | SOC 2 CC6.3, ISO 5.17 | MFA در IdP سازمان برای Admin و دسترسی‌های حساس اجباری باشد. | policy IdP، گزارش enrollment و exceptionهای مصوب. | Identity admin / ماهانه |
| IAM-04 | SOC 2 CC6.6, ISO 8.5 | SAML فقط SP-initiated باشد؛ IdP allowlist، issuer، audience، destination، recipient و `InResponseTo` اعتبارسنجی شوند. | metadata امضاشده، config review و نتایج test ACS. | Security engineering / هر تغییر |
| IAM-05 | SOC 2 CC6.6, ISO 8.24 | Response و assertion امضاشده و در سطح نیازمندی داده encrypted باشد؛ الگوریتم ضعیف ممنوع شود. | policy toolkit، گواهی pinned، test signature invalid. | Security engineering / هر تغییر |
| IAM-06 | SOC 2 CC6.6, ISO 8.5 | RelayState، SAML request، authorization code و assertion ID تک‌بارمصرف و TTLدار در Redis اتمی نگهداری شوند. | test replay، Redis config و audit event. | Platform / هر release |
| IAM-07 | SOC 2 CC6.1, ISO 5.18 | scope tenant از token معتبر و resource سازمانی استخراج شود؛ resource غیربومی با 404 پاسخ گیرد. | تست isolation و review queryهای repository. | Backend/Security / هر release |
| IAM-08 | SOC 2 CC6.1, ISO 8.2 | تصمیم مجوز server-side و per-action باشد؛ UI هیچ مجوزی را تعیین نکند. | کد `require_permission`، تست 401/403/404 و audit log. | Backend / هر release |
| IAM-09 | SOC 2 CC6.1, ISO 5.18 | بازبینی دسترسی privileged و export/audit دست‌کم فصلی انجام شود. | access review با تایید مدیر و اصلاحات. | Security / فصلی |
| IAM-10 | SOC 2 CC6.7, ISO 5.17 | secret، private key و certificate در secret manager/KMS باشند، هرگز در repo، installer یا log نباشند. | secret scan، KMS policy، rotation record. | Platform / ماهانه |
| IAM-11 | SOC 2 CC7.2, ISO 8.16 | رخدادهای login، ACS failure، permission denied، role change و export audit ثبت و به SIEM ارسال شوند. | schema audit، dashboard و alert test. | SOC / پیوسته |

## ۳. امنیت محصول، Secure SDLC و انتشار Windows

این بخش به SOC 2 CC7 و CC8 و کنترل‌های ISO برای secure development، change management، vulnerability management و configuration management نگاشت می‌شود. هر تغییر در Trust Center، policy کیفیت یا Control Plane باید به یک issue، review و نتیجهٔ آزمون قابل‌ردیابی متصل باشد.

| شناسه | کنترل و نگاشت | پیاده‌سازی مورد انتظار در DataSense | شاهد قابل‌قبول | مالک / تناوب |
|---|---|---|---|---|
| SDLC-01 | SOC 2 CC8.1, ISO 8.32 | تغییرات production از PR با حداقل یک review مستقل و CI سبز عبور کنند. | branch protection، PR نمونه، log CI. | Engineering / هر تغییر |
| SDLC-02 | SOC 2 CC7.1, ISO 8.8 | dependency scanning، SCA و رسیدگی به CVE با SLA مبتنی بر severity فعال باشد. | SBOM، گزارش scan و tickets remediation. | AppSec / هر release |
| SDLC-03 | SOC 2 CC7.1, ISO 8.25/8.27 | threat model برای SAML، token، export، PII scan، plugin و update flow بازبینی شود. | threat model و action register. | AppSec / هر feature حساس |
| SDLC-04 | SOC 2 CC7.1, ISO 8.28 | SAST، secret scanning و code review روی branch اصلی اجباری باشد. | workflow CI و نتیجهٔ scan. | AppSec / هر PR |
| SDLC-05 | SOC 2 CC8.1, ISO 8.9 | build runner pinned، dependency lock و artifact provenance قابل‌بازسازی باشد. | workflow، lockfile و build log. | DevOps / هر release |
| SDLC-06 | SOC 2 CC6.1, ISO 8.24 | امضای code-signing برای EXE/Setup و hashهای SHA-256 برای تمام release assets منتشر شود. | certificate inventory، `signtool verify` و checksums. | Release manager / هر release |
| SDLC-07 | SOC 2 CC7.4, ISO 8.29 | قبل از انتشار، unit، integration، UI smoke، negative SAML و rollback test اجرا شوند. | test report و release approval. | QA/Engineering / هر release |
| SDLC-08 | SOC 2 CC8.1, ISO 8.32 | release notes شامل تغییر امنیتی، migration، breaking change و CVE حل‌شده باشد. | GitHub Release و CHANGELOG. | Product/Release / هر release |
| SDLC-09 | SOC 2 CC7.2, ISO 8.15 | logهای اپلیکیشن PII، assertion، access token، refresh token و raw dataset را ثبت نکنند. | logging test و redaction review. | Engineering / هر release |

## ۴. Trust Center، کیفیت داده و حریم خصوصی

Trust Center باید تصمیم‌پذیر، محلی و قابل‌ممیزی بماند. نتیجهٔ scan فقط metadata طبقه‌بندی را نگه می‌دارد؛ مقدار نمونهٔ PII نباید در فایل export، log یا history وارد شود. فرمول score و policy gate مستقل‌اند: score بیانگر evidence است و gate تصمیم انتشار/پذیرش آن evidence را می‌سازد.

| شناسه | کنترل و نگاشت | پیاده‌سازی مورد انتظار در DataSense | شاهد قابل‌قبول | مالک / تناوب |
|---|---|---|---|---|
| DATA-01 | SOC 2 PI1.1, ISO 8.11 | contract برای داده‌های حساس، business owner، version و rule severity داشته باشد. | `.dsproj`، approval مالک داده و rule inventory. | Data Steward / هر قرارداد |
| DATA-02 | SOC 2 PI1.1, CC5.2 | محاسبهٔ weighted score deterministic باشد و rule error از pass جدا ثبت شود. | test unit و JSON audit evidence. | Engineering / هر release |
| DATA-03 | SOC 2 PI1.2, ISO 8.15 | Quality Gate با minimum score، maximum critical/high failures و block-on-error مصوب باشد. | policy export، change approval و gate history. | Data owner / هر قرارداد |
| DATA-04 | SOC 2 CC4.1, ISO 8.16 | trend کیفیت نگهداری و decline معنادار alert شود. | history privacy-preserving و dashboard/alert. | Data Steward / ماهانه |
| DATA-05 | SOC 2 C1.1, ISO 5.12/5.34 | classification PII قبل از export، sharing یا cloud connector بازبینی شود. | گزارش scan و exception approval. | Privacy/Data owner / هر dataset |
| DATA-06 | SOC 2 C1.2, ISO 8.12 | export دادهٔ Restricted با approval، policy، encryption و logging همراه باشد. | event export، policy decision و KMS evidence. | Data owner / هر export حساس |
| DATA-07 | SOC 2 PI1.5, ISO 8.10 | retention و secure deletion برای فایل پروژه، exports و cache محلی تعریف شود. | retention schedule و deletion test. | Product/IT / شش‌ماهه |
| DATA-08 | SOC 2 CC6.6, ISO 8.3 | داده و metadata چندسازمانی با `organization_id` و RLS/tenant checks جدا شوند. | SQL policy، integration test isolation. | Backend / هر release |

## ۵. عملیات، دسترس‌پذیری و پاسخ به رخداد

این بخش به SOC 2 CC7، CC9 و Availability Criteria و کنترل‌های ISO برای monitoring، backup، redundancy و continuity متصل است. محیط‌های production، staging و development باید حساب‌ها، secrets و دادهٔ آزمایشی جدا داشته باشند.

| شناسه | کنترل و نگاشت | پیاده‌سازی مورد انتظار در DataSense | شاهد قابل‌قبول | مالک / تناوب |
|---|---|---|---|---|
| OPS-01 | SOC 2 CC7.2, ISO 8.16 | alert برای authentication failure، replay، privilege change، export حساس و CI failure تعریف شود. | rule SIEM و exercise alert. | SOC / ماهانه |
| OPS-02 | SOC 2 CC7.3, ISO 5.24–5.27 | incident plan شامل triage، containment، evidence preservation، اطلاع‌رسانی و postmortem باشد. | playbook و tabletop exercise. | Incident commander / شش‌ماهه |
| OPS-03 | SOC 2 A1.2, ISO 8.13 | backup رمزنگاری‌شده برای PostgreSQL/config و restore تست‌شده با RPO/RTO مصوب باشد. | restore report و backup policy. | Platform / فصلی |
| OPS-04 | SOC 2 A1.2, ISO 8.14 | health checks، capacity threshold و availability monitoring برای Control Plane فعال باشد. | dashboard uptime و capacity review. | SRE / ماهانه |
| OPS-05 | SOC 2 CC9.1, ISO 5.19–5.22 | vendor risk برای IdP، GitHub Actions، signing CA، hosting و telemetry انجام شود. | vendor register، DPA/SOC report و review. | Procurement/Security / سالانه |
| OPS-06 | SOC 2 CC9.2, ISO 5.30 | BCP/DR برای outage IdP، compromise signing key، ransomware و loss CI runner تمرین شود. | سناریوی DR و evidence restore/rekey. | BCP owner / سالانه |
| OPS-07 | SOC 2 CC6.8, ISO 8.20/8.21 | production شبکه‌ای segment، TLS اجباری، admin endpoint محدود و WAF/rate limit داشته باشد. | network diagram، config proxy و penetration test. | Platform/Security / فصلی |
| OPS-08 | SOC 2 CC6.6, ISO 8.17 | clock synchronization در IdP، Control Plane، DB و SIEM برقرار باشد. | NTP config و drift report. | Platform / ماهانه |

## برنامهٔ نمونه‌گیری و مدیریت شواهد

ممیز باید در هر دوره دست‌کم یک release، یک تغییر role، یک offboarding، یک شکست SAML، یک export Trust Center، یک restore و یک incident drill را از ابتدا تا انتها ردیابی کند. هر شاهد باید URL/مسیر، hash یا شناسهٔ immutable، صاحب شاهد، زمان تولید و کنترل مربوط را داشته باشد. assertion، access token، secret و مقدار خام PII هرگز شاهد قابل‌الحاق به پروندهٔ audit نیستند؛ به‌جای آن از hash، event ID و screenshot redacted استفاده شود.

| حوزه | نمونه‌گیری حداقلی | معیار پذیرش |
|---|---|---|
| Access review | ۱۰ عضویت یا همهٔ privilegedها (هرکدام بیشتر است) | نقش، مدیر تأییدکننده، تاریخ review و اقدام اصلاحی کامل باشد. |
| Release | آخرین release Windows و یک hotfix | PR، scan، test، hash، امضا و approval قابل‌ردیابی باشد. |
| SAML | یک assertion معتبر و چهار negative case | signature، expiry، audience/destination mismatch و replay reject شوند. |
| Trust Center | دو قرارداد با severity متفاوت | score، gate، history و export بدون PII raw باشد. |
| Backup/DR | یک database restore و یک rotation key | RTO/RPO در محدودهٔ مصوب و شواهد کامل باشد. |

## اولویت‌بندی اصلاحات

در ۳۰ روز نخست، کنترل‌های IAM-04 تا IAM-10، SDLC-01 تا SDLC-06، DATA-03 و OPS-03 باید به سطح Pass برسند؛ زیرا compromise هویت، release artifact یا داده می‌تواند بیشترین اثر را داشته باشد. سپس monitoring، vendor risk و تمرین DR به‌ترتیب در ۶۰ و ۹۰ روز تکمیل شوند. هر مورد Partial یا Fail باید یک ticket با severity، مالک، موعد، کنترل جبرانی و معیار بسته‌شدن داشته باشد.

## منابع

[1]: https://www.iso.org/standard/27001 "ISO/IEC 27001:2022 — Information security management systems"
[2]: https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022 "AICPA — 2017 Trust Services Criteria, revised points of focus"
[3]: https://pages.nist.gov/800-63-3/sp800-63c.html "NIST SP 800-63C — Federation and assertion guidance (page notes SP 800-63-4 as the current revision)"
[4]: https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet.html "OWASP — SAML Security Cheat Sheet"
