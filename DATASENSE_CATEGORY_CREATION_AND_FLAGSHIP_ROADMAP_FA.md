# DataSense: ایجاد دستهٔ «Proof-Carrying Decisions»

**نسخهٔ سند:** ۱.۰ — ۲۳ اوت ۲۰۲۶
**وضعیت:** فرضیهٔ استراتژیک و نقشهٔ ساخت؛ ادعای برتری یا Product-Market Fit نیست.

## تز مرکزی

بازار در حال حاضر ابزارهای زیادی برای **مشاهدهٔ داده**، **quality monitoring**، **catalog/lineage** و **governance AI agent** دارد. اما این لایه‌ها غالباً یک پرسش عملی را جداگانه حل می‌کنند: «آیا یک تصمیم، export، گزارش یا action بیرونی که از داده ساخته شده، *همین اکنون* مجاز است و آیا می‌توان بعداً به‌طور قابل‌راستی‌آزمایی اثبات کرد چرا مجاز یا مسدود شد؟»

DataSense نباید با ادعای «یک data platform دیگر» وارد این فضای شلوغ شود. دستهٔ پیشنهادی آن **Proof-Carrying Decisions** است:

> **هر تصمیم یا action داده‌محور، پیش از عبور از یک trust boundary، یک Decision Receipt قابل‌خواندن برای انسان و قابل‌راستی‌آزمایی برای ماشین حمل می‌کند.**

Decision Receipt به‌جای انتقال دادهٔ خام، شناسه‌های cryptographic، fingerprint، lineage، نتیجهٔ Contract/Quality Gate/Schema Drift، policy version، scope action، تصمیم، دلیل bounded و approvalهای لازم را ثبت می‌کند. تصمیم بدون Receipt معتبر یا با Receipt منقضی/نامنطبق، باید fail-closed شود.

این تز از روندهای مشاهده‌شده در منابع بازار پشتیبانی می‌کند: قراردادهای اجرایی و approval انسانی برای workflowهای agentic، metadata و lineage پیوسته، policy enforcement در runtime و کنترل پیش از action به‌جای alert پس از action.[1] [2] [3] بااین‌حال، تفاوت DataSense باید در تجربهٔ محصول و proof قابل‌حمل باشد، نه صرفاً تکرار واژه‌های «AI governance» یا «observability».

## 1. چرا این می‌تواند یک category جدید بسازد

| دستهٔ رایج | پرسش اصلی | نقطهٔ کور معمول | پاسخ پیشنهادی DataSense |
|---|---|---|---|
| Data observability | «چه چیزی خراب یا غیرعادی شد؟» | اغلب بعد از وقوع signal می‌دهد. | پیش از export/action، trust decision قطعی صادر یا action را block می‌کند. |
| Data catalog/lineage | «داده از کجا آمد و چه وابستگی دارد؟» | lineage به‌تنهایی مجوز action نیست. | lineage را به یک receipt امضاشده و action-scoped تبدیل می‌کند. |
| Data quality | «آیا داده با ruleها سازگار است؟» | نتیجهٔ quality به workflow business/action وصل نیست. | Quality Gate یکی از inputs اجباری Decision Gate است. |
| AI governance | «کدام agent چه permission و trace دارد؟» | اغلب agent-centric یا post-event است. | هر actor—تحلیل‌گر، script یا agent—برای action داده‌محور یک proof یکسان نیاز دارد. |
| GRC/evidence | «چه evidenceی برای ممیزی داریم؟» | evidence دوره‌ای و خارج از workflow است. | evidence در لحظهٔ تصمیم تولید، امضا و قابل‌verify می‌شود. |

### وضعیت مطلوب برای مشتری

یک تحلیل‌گر در Windows، یک pipeline داخلی یا یک AI agent ممکن است بخواهد report، dashboard، export، recommendation یا trigger تولید کند. DataSense قبل از آن، با همان قرارداد داده و policy سازمانی، یکی از سه خروجی شفاف را می‌دهد: **allow with receipt**، **require approval** یا **block with bounded reason**. خروجی همراه action حرکت می‌کند و receiver می‌تواند آن را offline verify کند، بدون اینکه rowها یا PII را ببیند.

این نقطهٔ اتصال، هم ارزش فوری برای تحلیل‌گر دارد و هم مسیر ورود طبیعی به enterprise، AI governance و automation را می‌سازد، بی‌آنکه local-first/privacy-first بودن DataSense قربانی شود.

## 2. محصول flagship: DataSense Decision Fabric

### 2.1 محصول اولیهٔ قابل‌ساخت: Trust Decision Receipt

اولین قابلیت flagship باید کوچک، قابل‌اثبات و متصل به Trust Center فعلی باشد: **Trust Decision Receipt**.

| جزء | تعریف v1 | مرز امنیت/حریم خصوصی |
|---|---|---|
| Action Intent | نوع action مانند `export.csv`، `report.html`، `dashboard.html`، `agent.recommendation` یا `agent.external_action`; scope و purpose bounded | مسیر فایل، recipient، URL، prompt یا dataset values مجاز نیستند. |
| Trust Inputs | digest bundle evidence، schema/lineage fingerprint، Quality Gate، Schema Drift، policy version و freshness | فقط metadata و digest؛ دادهٔ خام وارد receipt نمی‌شود. |
| Decision Policy | allow / approval-required / block بر اساس gate، drift، sensitivity و action risk | policy versioned، deterministic و fail-closed است. |
| Receipt | canonical JSON، digest، signature، expiry و key ID | tamper-evident و offline-verifiable. |
| Verification | CLI/API/local UI برای validate signature، expiry، action scope و evidence binding | key resolver local/enterprise؛ secret هرگز export نمی‌شود. |
| Decision Ledger | history append-only از metadata receiptها | retention/minimization و tenant/user separation الزامی است. |

### 2.2 تجربهٔ کاربر که باید «جادو» به‌نظر برسد

کاربر پس از اجرای Trust Center، به‌جای صرفاً دیدن score، روی **Prepare Trusted Export** می‌زند. در کمتر از چند ثانیه یک صفحهٔ ساده می‌بیند: «این export برای `external_share` **blocked** است چون quality gate/policy/schema drift X؛ برای export داخلی اجازه با receipt شماره Y صادر می‌شود.» اگر اجازه صادر شود، فایل receipt کنار artifact قرار می‌گیرد و دریافت‌کننده می‌تواند آن را بدون دادهٔ خام verify کند.

به‌این‌ترتیب، DataSense از «ابزار analysis با trust tab» به **control surface برای داده‌ای که قرار است تصمیم بسازد یا حرکت کند** تبدیل می‌شود.

## 3. قابلیت‌هایی که در صورت اجرای درست بازار را دنبال خود می‌کشند

| موج | قابلیت | چرا distinctive است | معیار موفقیت پیش از scale |
|---|---|---|---|
| W1 | Trust Decision Receipts | proof قابل‌حمل برای action، نه فقط audit export | ۳ design partner بتوانند receipt را در review واقعی verify کنند. |
| W1 | Action Gate در Desktop | جلوگیری یا approval برای export/report از همان workflow analyst | time-to-first-trusted-export کمتر از ۵ دقیقه؛ bypass rate اندازه‌گیری‌شده. |
| W2 | Policy Simulator / Counterfactual Lab | نشان می‌دهد policy جدید چه actionهای گذشته/آینده را block می‌کرد، بدون اجرای واقعی | owner policy بتواند قبل از deploy blast radius را ببیند. |
| W2 | Evidence Graph | graph receipt ↔ bundle ↔ contract ↔ lineage ↔ action ↔ approval | root cause یا audit question در کمتر از ۵ دقیقه پاسخ داده شود. |
| W2 | AI Agent Trust Gateway | MCP/CLI/API که agent قبل از read/export/tool action receipt می‌گیرد | agent بدون receipt معتبر نتواند action مجاز را bypass کند. |
| W3 | Verifiable Trust Exchange | receiver SDK و public verification profile برای vendor/customer handoff | یک receiver مستقل receipt را offline validate کند. |
| W3 | Privacy-preserving Benchmark Network | فقط aggregate/opt-in control coverage و policy patterns، نه customer data | ارزش شبکه بدون نشت داده ثابت شود. |
| W4 | Domain Trust Packs | policy/contract/action template برای مالی، سلامت، تولید و regulated analytics | هر pack با design partner و evidence واقعی co-design شود. |

## 4. مزیت‌های دفاع‌پذیر

**دادهٔ خام یا یک مدل AI moat نیست.** مزیت مشروع باید از چهار حلقهٔ به‌هم‌پیوسته شکل بگیرد: workflow local-first، grammar استاندارد Receipt، history قابل‌verify، و distribution داخل ابزارهای داده.

| حلقهٔ moat | دارایی | چرا کپی‌کردن آن دشوارتر از feature است |
|---|---|---|
| Trust grammar | schema باز اما دقیق Receipt، reason codeها، action taxonomy و verifier reference | اکوسیستم receiver/approval روی compatibility قرارداد می‌بندد. |
| Workflow embedding | action gate در desktop، CLI و agent interfaces | receipt بخشی از رفتار روزانه می‌شود، نه یک dashboard تزئینی. |
| Evidence history | زنجیرهٔ bundle، decision، policy و approval با hash/signature | value با تکرار workflow انباشته و قابل‌حمل می‌شود. |
| Policy intelligence | counterfactual simulator و templateهای domain با feedback human | quality policy به‌مرور context پیدا می‌کند، اما auto-change بدون approval ممنوع است. |
| Privacy architecture | raw data never leaves default boundary؛ receiver با proof کار می‌کند | برای regulated/local-first buyer یک constraint product، نه marketing claim. |

## 5. معماری پیشنهادی

```text
Data / lineage / contract / drift / sensitivity
                 │
                 ▼
       Trust Inputs Normalizer
                 │
                 ▼
    Deterministic Decision Policy Engine
                 │
      ┌──────────┼───────────┐
      ▼          ▼           ▼
    BLOCK   APPROVAL_REQUIRED  ALLOW
      │          │           │
      └──────────┴───────────┘
                 ▼
    Signed Action-Scoped Decision Receipt
                 │
        ┌────────┴─────────┐
        ▼                  ▼
Action Gate             Offline Verifier
Desktop / CLI / Agent   Customer / Auditor / API
```

### غیرقابل‌مذاکره‌ها

1. **Fail-closed:** report/gate/schema/lineage absent یا stale، policy unknown، signature invalid، action mismatch یا expiry باید `block` تولید کند.
2. **No raw data:** receipt، ledger، metric و approval فقط metadata bounded و digest نگه می‌دارند.
3. **Action-scoped:** Receipt `export.csv` برای `agent.external_action` معتبر نیست.
4. **Policy/version binding:** receipt به digest evidence و policy version متصل است؛ تغییر policy یا data state آن را invalid می‌کند.
5. **Approval is additive:** approval هیچ‌گاه quality/sensitivity/circuit block را override نمی‌کند مگر policy صریحاً exception boundary تعریف کند.
6. **Local-first default:** v1 بدون cloud dependency قابل‌استفاده است؛ Control Plane اختیاری فقط برای enterprise ledger, RBAC و centralized key/approval می‌آید.

## 6. برنامهٔ ساخت 12 ماهه

| بازه | خروجی قابل‌استفاده | شرط توقف یا بازطراحی |
|---|---|---|
| 0–30 روز | v1 Decision Receipt Core، sign/verify CLI، tests tamper/expiry/scope؛ UI export receipt | اگر ۵ مصاحبه نشان دهد proof قابل‌حمل مسئله نیست، روی Action Gate ساده تمرکز شود. |
| 31–60 روز | Desktop Action Gate برای export/report، policy profiles و receipt viewer | اگر bypass ترجیح داده شود، friction workflow و value message بازطراحی شود. |
| 61–90 روز | Design-partner pilot، receiver verifier و evidence graph prototype | اگر buyer صرفاً dashboard بخواهد، positioning/segment narrow شود. |
| 3–6 ماه | Policy Simulator، approval workflow، enterprise key/RBAC binding و CLI integration | فقط پس از استفادهٔ تکراری و sponsor اقتصادی. |
| 6–12 ماه | Agent Trust Gateway، SDK/receiver ecosystem و domain trust packs | فقط پس از deterministic controls و security review. |

## 7. چه چیزی را عمداً نمی‌سازیم

DataSense نباید به‌طور هم‌زمان جایگزین warehouse، catalog، lakehouse، notebook، generic BI، GRC suite یا LLM platform شود. همچنین نباید «auto-remediation» یا agent action بدون deterministic policy، approval boundary و rollback evidence بفروشد. تمرکز category-creating در سال اول: **تصمیم‌های داده‌محور proof-carrying و action-gated**.

## 8. شاخص‌های اعتبارسنجی

| فرضیه | شاخص | target اولیهٔ پایلوت | تفسیر شکست |
|---|---|---:|---|
| H-PCD-1 | زمان ایجاد اولین receipt | کمتر از ۵ دقیقه | onboarding یا language محصول نامناسب است. |
| H-PCD-2 | receipt verification توسط receiver مستقل | ۲ از ۳ design partner | trust exchange هنوز value واقعی نمی‌سازد. |
| H-PCD-3 | actionهایی که با policy واقعی review/block شدند | حداقل ۱۰ per pilot بدون bypass | product surface به action واقعی متصل نشده است. |
| H-PCD-4 | contract/receipt reuse | بیش از ۴۰٪ بعد از هفتهٔ چهارم | workflow sticky نیست یا policy generic است. |
| H-PCD-5 | sponsor اقتصادی/security | حداقل ۲ از ۳ | decision proof به procurement risk وصل نشده است. |

## References

[1] [Soda — AI for Data Quality, June 2026](https://soda.io/blog/ai-for-data-quality)

[2] [Acceldata — What “Good” Data Governance Looks Like in 2026](https://www.acceldata.io/blog/what-modern-data-governance-actually-looks-like-in-2026)

[3] [Drata — Introducing AI Agent Governance, June 2026](https://drata.com/blog/introducing-ai-agent-governance)
