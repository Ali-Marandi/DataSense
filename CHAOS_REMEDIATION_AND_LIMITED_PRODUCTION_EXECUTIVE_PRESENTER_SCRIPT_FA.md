# اسکریپت Executive Briefing: Chaos Remediation و Limited Production On-Call

## مشخصات ارائه

| مورد | مقدار |
|---|---|
| مخاطب | هیئت‌مدیره، Release Owner، Security، SRE، Product و Engineering Leadership |
| زمان پیشنهادی | ۱۲ تا ۱۵ دقیقه + ۱۰ دقیقه پرسش‌وپاسخ |
| پیام مرکزی | شواهد model مفید است، اما evidence staging معیار تصمیم است؛ سرعت rollout نباید بر fail-closed compliance غالب شود. |
| تصمیم مورد درخواست | تأیید اجرای Wave A/B/C با synthetic staging، سپس تصمیم Limited Production بر پایهٔ evidence و sign-off. |
| ادعای ممنوع | آماده‌بودن Broad Production یا PASS بودن سناریوهای اجرا‌نشده. |

> لحن ارائه باید آرام، دقیق و evidence-driven باشد. از عبارت‌هایی مانند «به‌طور کامل امن است» یا «قطعاً آمادهٔ تولید است» استفاده نکنید. به‌جای آن بگویید «در محدودهٔ شواهد فعلی» و «پس از تکمیل گیت‌های مشخص‌شده».

---

## اسلاید ۱ — تصمیم: evidence پیش از سرعت

**زمان:** ۶۰ ثانیه

**متن گفتار:**

«امروز دربارهٔ ارسال پیام بیشتر یا افزایش سریع rollout تصمیم نمی‌گیریم. موضوع تصمیم این است که آیا مسیر activation می‌تواند تحت فشار، خطای policy و خرابی worker، اثر خارجی ناخواسته ایجاد نکند. ما مسیر را به‌گونه‌ای طراحی کرده‌ایم که هر ambiguity به suppression برسد؛ بنابراین موفقیت در این مرحله با throughput اندازه‌گیری نمی‌شود، بلکه با اثبات نبود اثر غیرمجاز اندازه‌گیری می‌شود. درخواست من این است که Wave A تا C را با scope مصنوعی و staging تأیید کنیم و هر افزایش cohort را به evidence واقعی گره بزنیم.»

**انتقال:** «ابتدا باید روشن کنیم چه چیزی واقعاً اثبات شده و چه چیزی هنوز فقط طراحی یا مدل است.»

---

## اسلاید ۲ — baseline صادقانه: ۶ PASS، ۳ PARTIAL، ۷ NOT RUN

**زمان:** ۷۵ ثانیه

**متن گفتار:**

«در register شانزده سناریوی chaos، شش concept در مدل deterministic پاس شده‌اند، سه مورد partial و هفت مورد اصلاً در staging اجرا نشده‌اند. این شفافیت یک ضعف گزارش نیست؛ مکانیزم جلوگیری از greenwashing عملیاتی است. چهار pytest و یک harness in-memory، رفتارهایی مثل Open شدن circuit، عدم auto-resume، policy denial، recipient verification، idempotency و kill switch را در مدل بررسی می‌کنند. اما این harness به Kubernetes، PostgreSQL، Alertmanager یا provider واقعی وصل نیست. بنابراین status فعلی، PASS model است نه PASS staging و نه مجوز تولید.»

**نکتهٔ کلیدی:** عدد شش به scenario concept اشاره دارد؛ نه شش آزمون مستقل production-grade.

**انتقال:** «برای بستن این فاصله، remediation را بر اساس خطر، نه صرفاً راحتی توسعه، ترتیب داده‌ایم.»

---

## اسلاید ۳ — Wave A: ساختن مرزهای fail-closed

**زمان:** ۹۰ ثانیه

**متن گفتار:**

«Wave A پایه‌ای است که هیچ test integration معناداری بدون آن نداریم. ابتدا policy، consent، recipient، channel و circuit باید دقیقاً قبل از delivery دوباره ارزیابی شوند. سپس state activation، audit، suppression و Outbox enqueue باید در یک transaction tenant-scoped ثبت شوند. execution ledger یکتا لازم است تا duplicate، retry یا lease recovery حداکثر یک effect خارجی بسازند. در کنار آن، controller باید state circuit را persistent نگه دارد و input alert فقط با HMAC یا mTLS، freshness و replay protection پذیرفته شود. این‌ها featureهای اختیاری نیستند؛ شرایط لازم برای ادعای fail-closed هستند.»

**تأکید:** «اگر policy missing باشد، نتیجه باید suppress باشد؛ نه retry و نه fallback.»

**انتقال:** «Security greenlight Wave A دقیقاً روی همین مرزها تصمیم می‌گیرد.»

---

## اسلاید ۴ — Security greenlight: evidence، نه trust

**زمان:** ۹۰ ثانیه

**متن گفتار:**

«برای Wave A، از Security امضای کلی درخواست نمی‌کنیم؛ یک checklist قابل‌آزمون داریم. Reviewer باید ببیند revocation پس از enqueue، provider call را صفر می‌کند؛ resolver نامعتبر delivery را suppress می‌کند؛ state Unknown به suppress می‌رسد؛ RLS از cross-tenant دسترسی جلوگیری می‌کند؛ unique execution key اثر را یکی نگه می‌دارد؛ و هیچ payload، recipient یا secret در log و metric نیست. علاوه بر این، controller forged یا replayed alert را رد می‌کند و Close بدون approval مجاز نیست. اگر هر کدام از این کنترل‌ها evidence ندارد، تصمیم درست Reject یا محدودکردن scope است؛ نه موافقت مشروط مبهم.»

**انتقال:** «پس از Wave A، Wave B و C شواهد را از سطح integration به رفتار واقعی staging منتقل می‌کنند.»

---

## اسلاید ۵ — Wave B و C: از integration تا game day

**زمان:** ۷۵ ثانیه

**متن گفتار:**

«Wave B با PostgreSQL، Redis و fake provider ایزوله، مسیرهای revocation، duplicate، timeout، permanent failure، payload rejection و tenant isolation را آزمایش می‌کند. Wave C این کنترل‌ها را در staging Kubernetes تحت فشار مشاهده می‌کند: pod-kill پس از claim، flood ده‌برابری، signed alert، circuit Open، rollback و پایداری migration. تمام داده‌ها synthetic هستند، provider واقعی وجود ندارد و commandها باید explicit non-production acknowledgement داشته باشند. نکتهٔ مهم این است که game day نباید برای یافتن design جدید باشد؛ باید implementation Wave A/B را در محیط نزدیک‌تر به واقعیت اثبات کند.»

**انتقال:** «دو سناریوی Wave C بیشترین ارزش را برای سنجش recovery و containment دارند.»

---

## اسلاید ۶ — C08: pod-kill پس از claim

**زمان:** ۷۵ ثانیه

**متن گفتار:**

«در C08، یک worker درست پس از claim کردن event و پیش از effect، به‌طور کنترل‌شده متوقف می‌شود. هدف، شکست دادن worker نیست؛ هدف اثبات این است که lease recovery و execution ledger با هم کار می‌کنند. شرط PASS ساده است: بعد از restart و recover شدن lease، fake provider حداکثر یک effect ثبت کند. اگر دو effect، state نامعتبر، retry loop یا cross-tenant evidence ببینیم، سناریو Fail است. همچنین انتظار داریم metric lease recovery، audit checkpoint و final terminal state در evidence card ثبت شوند. هیچ operator مجاز به اصلاح مستقیم database برای عبور دادن سناریو نیست.»

**انتقال:** «C15 سپس همین discipline را تحت حجم و lag بررسی می‌کند.»

---

## اسلاید ۷ — C15: flood ده‌برابری و circuit Open

**زمان:** ۹۰ ثانیه

**متن گفتار:**

«در C15، generator مصنوعی با ده برابر baseline و latency ساختگی fake provider، queue را تحت فشار می‌گذارد. وقتی oldest pending age برای دو دقیقه از ۹۰۰ ثانیه عبور کند، signed alert باید circuit را Open و release را freeze کند. معیار PASS این نیست که queue سریع خالی شود. معیار PASS این است که از لحظهٔ Open، external effect صفر باشد، triggerهای جدید به suppression bounded برسند، duplicate و retry loop ایجاد نشود، و alert در هدف زمانی P1 به SRE و Security برسد. recovery حق auto-close ندارد؛ فقط پس از سلامت پایدار، approval و canary محدود می‌توان Half-Open را بررسی کرد.»

**انتقال:** «همین پروتکل، مبنای عملیات on-call در Limited Production است.»

---

## اسلاید ۸ — عملیات Limited Production: pause پیش از bypass

**زمان:** ۹۰ ثانیه

**متن گفتار:**

«در cohort محدود، on-call با چهار کلاس severity کار می‌کند. P1 شامل هر compliance violation، revocation p95 بالاتر از پنج دقیقه، lag بالاتر از پانزده دقیقه و worker unavailable است. این alerts باید در پنج دقیقه acknowledge و در ده دقیقه contained شوند. Containment به معنی Open کردن circuit، pause کردن external channel، freeze release و حفظ audit است؛ نه redrive پیام‌های قدیمی و نه bypass policy. P2 برای lag بالای پنج دقیقه، dead ratio بالای یک درصد، retry ratio بالای بیست درصد، payload rejection burst و lease recovery loop است. P3ها مانند denial spike یا funnel stall، نیازمند تحلیل Product/Privacy/CS هستند؛ suppression خودکار در این موارد نباید دور زده شود.»

**انتقال:** «برای جلوگیری از noise و تصمیم‌های سلیقه‌ای، recovery نیز gate دارد.»

---

## اسلاید ۹ — recovery gate: انسان در حلقهٔ تصمیم

**زمان:** ۷۵ ثانیه

**متن گفتار:**

«از Open به Half-Open فقط وقتی می‌رویم که oldest pending age برای پانزده دقیقه زیر سیصد ثانیه باشد، worker healthy باشد، dead trend رشد نکند و از زمان Open هیچ compliance violation رخ نداده باشد. Half-Open نرخ canary را حداکثر پنج delivery در دقیقه نگه می‌دارد. SRE و Security باید Half-Open را تأیید کنند؛ برای Close، Product نیز اضافه می‌شود. هر failure در canary، circuit را به Open برمی‌گرداند. این عمداً سرعت را قربانی safety می‌کند، چون پیام دیر یا غیرمجاز معمولاً ارزش بیشتری از queue throughput ندارد.»

**انتقال:** «در پایان، تصمیم ما binary نیست؛ evidence تصمیم را تعیین می‌کند.»

---

## اسلاید ۱۰ — تصمیم و درخواست مصوبه

**زمان:** ۶۰ ثانیه

**متن گفتار:**

«درخواست ما سه بخش دارد. نخست، تأیید scope Wave A برای ساخت و test کنترل‌های fail-closed، بدون provider واقعی. دوم، تأیید اجرای Wave C فقط در staging synthetic با change window، kill switch و observers مشخص. سوم، پذیرش این rule که Limited Production تنها بعد از بسته‌شدن P0ها، PASS staging، alert routing و sign-offهای Security، SRE، Privacy، Engineering و Product بررسی می‌شود. Broad Production تا زمان PASS شدن همهٔ سناریوهای باقی‌مانده، rollback drill و closure CAPA روی میز نیست. این مسیر کندتر به نظر می‌رسد، اما ریسک trust، privacy و incident cost را پیش از افزایش cohort کنترل می‌کند.»

**پایان:** «اگر موافق باشید، Release Owner evidence register را با owner/date برای هر CAPA به جلسهٔ gate بعدی می‌آورد.»

---

## پاسخ‌های آماده به پرسش‌های محتمل

| پرسش | پاسخ پیشنهادی |
|---|---|
| چرا با ۶ PASS جلو نمی‌رویم؟ | چون شش PASS در model هستند، نه در dependency و staging واقعی. تفاوت آن‌ها در crash، RLS، network، alert routing و migration ظاهر می‌شود. |
| چرا triggerها را به‌سادگی retry نمی‌کنیم؟ | retry بدون policy re-check یا بعد از incident می‌تواند effect منقضی، غیرمجاز یا تکراری بسازد. fresh eligibility لازم است. |
| آیا ۱۵ دقیقه lag به معنای failure کل محصول است؟ | خیر؛ به معنی failure-safe برای scope activation است. Quality/Audit eventها باید با runbook مستقل خود باقی بمانند. |
| چرا Close خودکار نیست؟ | transient recovery می‌تواند policy یا provider failure پنهان کند. Close یک تصمیم risk-bearing است و evidence/approval می‌خواهد. |
| آیا این آستانه‌ها SLO نهایی هستند؟ | خیر. آستانه‌های cohort محدودند و پس از حداقل ۱۴ روز evidence پایدار calibrate می‌شوند. |
| چه چیزی rollout را متوقف می‌کند؟ | policy bypass، tenant isolation failure، kill-switch failure، sensitive telemetry، scenario critical بدون evidence یا هر P1 باز. |

## چک‌لیست تمرین

- [ ] از تمایز `model PASS`، `staging PASS` و production readiness در تمام اسلایدها استفاده کنید.
- [ ] عددها را دقیق بگویید: ۶ PASS model، ۳ PARTIAL و ۷ NOT RUN در baseline.
- [ ] هرگز promise زمان یا readiness ندهید؛ به gate و evidence ارجاع دهید.
- [ ] هنگام پرسش فنی، به fake provider، synthetic tenant، bounded metrics و human approval اشاره کنید.
- [ ] در پایان، هر سه درخواست مصوبه را تکرار و owner تصمیم بعدی را مشخص کنید.

## منابع داخلی

[1] `ACTIVATION_CHAOS_REMEDIATION_AND_PASS_CONVERSION_PLAN_FA.md`.

[2] `ACTIVATION_LIMITED_PRODUCTION_ONCALL_RUNBOOK_AND_ALERT_THRESHOLDS_FA.md`.

[3] `WAVE_A_SECURITY_VERIFICATION_AND_GREENLIGHT_CHECKLIST_FA.md`.

[4] `ACTIVATION_OUTBOX_CIRCUIT_BREAKER_AND_CHAOS_TEST_PLAN_FA.md`.
