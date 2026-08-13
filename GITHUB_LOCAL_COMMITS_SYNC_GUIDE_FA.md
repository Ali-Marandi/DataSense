# راهنمای اعمال commitهای محلی DataSense در GitHub

## وضعیت ثبت‌شده

در زمان تهیهٔ این راهنما، branch محلی `main` در مسیر `/home/ubuntu/datasense` شامل commitهای ثبت‌شده اما هنوز ارسال‌نشده به remote است. آخرین commit محلی `c1390ba` با عنوان `feat: add schema drift guard and stabilize PyQt tests` است. خروجی آخرین بررسی محلی نشان داد `HEAD` نسبت به ref محلی `origin/main` چهار commit جلوتر است. این عدد باید پیش از push دوباره بررسی شود، زیرا ارتباط DNS با GitHub در sandbox در زمان تلاش قبلی برقرار نبود و ref remote احتمالاً تازه نیست.

> از `git push --force` یا واردکردن token در command line، URL remote، history shell یا فایل پروژه استفاده نکنید. token قبلی که در گفتگو مطرح شده بود باید فوراً در GitHub revoke شود و هر token تازه باید فقط از طریق secret manager یا جریان ورود امن استفاده شود.

## پیش‌نیازهای امنیتی

| اقدام | دلیل | نتیجهٔ مطلوب |
|---|---|---|
| Revoke کردن credential افشاشده | token در گفتگو یا history قابل‌اعتماد نیست. | token قدیمی نامعتبر و ثبت‌شده در audit GitHub باشد. |
| ساخت credential جدید حداقلی | اصل least privilege. | برای push به repo خصوصی/عمومی، scope لازم و تاریخ انقضای کوتاه. |
| فعال‌سازی MFA و بررسی SSH keys/Apps | کاهش تصرف حساب. | فقط کلیدها و Appهای شناخته‌شده فعال باشند. |
| عدم قراردادن secret در repo | جلوگیری از اسکن و افشای مجدد. | `git grep` برای token/key خروجی نداشته باشد. |

اگر GitHub CLI روی رایانهٔ خودتان نصب است، ورود تعاملی امن‌ترین مسیر ساده است:

```bash
gh auth login --hostname github.com --git-protocol https --web
```

مرورگر باز می‌شود و تأیید هویت خارج از history shell انجام می‌گیرد. برای محیط‌های سازمانی، GitHub App یا fine-grained token محدود به همان repository و دارای expiration توصیه می‌شود.

## روش پیشنهادی: همگام‌سازی امن با push مستقیم

این روش فقط هنگامی مناسب است که شما مالک branch `main` باشید، branch protection اجازهٔ direct push بدهد و policy سازمان PR اجباری نداشته باشد.

### گام ۱ — وارد مسیر مخزن شوید و وضعیت محلی را ببینید

```bash
cd /home/ubuntu/datasense
git status --short
git branch --show-current
git log --oneline --decorate -6
```

انتظار می‌رود وضعیت working tree خالی باشد و branch `main` نمایش داده شود. اگر فایل تغییرکرده‌ای نمایش داده شد، قبل از ادامه آن را review و commit/stash کنید؛ برای push کردن تغییرهای نامشخص عجله نکنید.

### گام ۲ — اجرای آزمون نهایی

```bash
python3 -m pytest -q
```

نتیجهٔ آخرین validation این workspace، `79 passed, 2 warnings` بوده است. دو warning مربوط به deprecation در `joblib` هستند و failure نیستند. اگر خروجی جدید متفاوت است، ابتدا علت تفاوت را حل کنید و سپس اقدام کنید.

### گام ۳ — بررسی remote و دریافت وضعیت تازه

```bash
git remote -v
git fetch --prune origin
git status -sb
git log --oneline --left-right origin/main...main
```

`git fetch` فقط metadata را به‌روزرسانی می‌کند و فایل کاری شما را تغییر نمی‌دهد. این مرحله برای تشخیص commitهای جدید روی GitHub ضروری است. در صورت مشاهدهٔ خطای `Could not resolve host: github.com`، مشکل DNS/network را حل کنید و هیچ credential جدیدی را به‌عنوان راه‌حل آن خطا وارد نکنید.

### گام ۴ — بررسی سریع secrets قبل از انتشار

```bash
git grep -nEi '(ghp_|github_pat_|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|AWS_SECRET_ACCESS_KEY)' -- . ':!*.lock' || true
git diff --check origin/main...main
```

اگر مورد واقعی secret مشاهده شد، commit را push نکنید. secret باید revoke شود و با `git filter-repo` یا ابزار رسمی rewrite history حذف شود؛ حذف سادهٔ خط در یک commit جدید برای secret قبلاً commit‌شده کافی نیست.

### گام ۵ — ارسال امن

اگر `main` فقط جلوتر بود و policy اجازه می‌داد:

```bash
git push origin main
git status -sb
git log -1 --oneline origin/main
```

بعد از موفقیت، commit `c1390ba` باید در history `origin/main` دیده شود و `git status -sb` نباید ahead count نشان دهد.

## اگر GitHub commit جدیدتری داشت: مسیر بدون force

اگر `git fetch` نشان داد `origin/main` جلوتر است، ابتدا تغییرهای remote را بررسی کنید:

```bash
git log --oneline main..origin/main
git diff --stat main..origin/main
```

سپس با rebase و بدون force همگام شوید:

```bash
git pull --rebase origin main
# در صورت conflict: فایل‌ها را اصلاح کنید، سپس
# git add <resolved-files>
# git rebase --continue
python3 -m pytest -q
git push origin main
```

اگر rebase نامناسب بود یا conflict شامل کد حساس/معماری است، عملیات را متوقف کنید:

```bash
git rebase --abort
```

و به‌جای direct push از branch و pull request استفاده کنید.

## روش سازمانی ترجیحی: branch و Pull Request

اگر `main` محافظت‌شده است یا code review لازم است، این مسیر مناسب‌تر است. از آنجا که commitها در حال حاضر روی branch محلی `main` هستند، ابتدا branch انتشار می‌سازیم؛ هیچ history بازنویسی نمی‌شود.

```bash
cd /home/ubuntu/datasense
git fetch --prune origin
git switch -c release/schema-drift-guard
git push -u origin release/schema-drift-guard
```

سپس در GitHub یک Pull Request از `release/schema-drift-guard` به `main` بسازید. متن پیشنهادی PR:

> **Title:** Add Schema Drift Guard and stabilize headless PyQt tests  
> **Summary:** Adds privacy-preserving schema snapshots, compatibility policies, project persistence, Trust Center controls, technical documentation and a repository-wide offscreen Qt test bootstrap.  
> **Validation:** `79 passed, 2 warnings`; JUnit evidence and validation report included.  
> **Risk:** UI additions are additive; schema policy defaults accept added columns and block removal/type/nullability relaxation.  
> **Rollback:** Revert commit `c1390ba` after confirming no downstream project requires its baseline/policy manifest fields.

پس از review، CI و approvalهای لازم، PR را merge کنید. برای branch protection، این روش از bypass کردن کنترل‌های سازمانی جلوگیری می‌کند.

## تشخیص خطاهای متداول

| خطا | علت محتمل | اقدام درست |
|---|---|---|
| `Could not resolve host: github.com` | DNS یا network sandbox قطع است. | DNS/VPN/network را بررسی و بعد `git fetch` را تکرار کنید؛ token را عوض نکنید. |
| `Authentication failed` | credential منقضی یا scope ناکافی است. | با `gh auth login --web` یا credential جدید حداقلی ورود کنید. |
| `rejected non-fast-forward` | روی remote commit جدید وجود دارد. | `git fetch`، review، سپس `git pull --rebase` یا PR؛ force نکنید. |
| `protected branch hook declined` | policy نیازمند PR/approval/CI است. | branch منتشر و Pull Request ایجاد کنید. |
| secret scan failure | secret واقعی یا pattern حساس در commit وجود دارد. | push را متوقف، revoke و history را مطابق policy پاکسازی کنید. |

## تأیید نهایی پس از انتشار

```bash
git fetch --prune origin
git status -sb
git log --oneline -4 origin/main
git ls-remote --heads origin main
```

علاوه بر خروجی Git، صفحهٔ **Actions** و **Pull Requests/Commits** repository را در GitHub باز کنید. باید CI مربوط به commit جدید سبز باشد، commit `c1390ba` یا merge commit معادل آن در `main` دیده شود و هیچ secret scanning alert باز نماند.

## نکتهٔ انتشار نسخه

این commit شامل feature و مستندات است، اما به‌تنهایی به‌معنای ساخت release binary جدید نیست. پیش از ایجاد tag/release جدید، نسخه در `core/version.py`، release notes، build workflow Windows و artifactهای امضاشده باید با policy انتشار به‌روزرسانی و اعتبارسنجی شوند. از بازنویسی tag منتشرشدهٔ `v2.2.1` پرهیز کنید؛ برای انتشار بعدی، version و tag جدید بسازید.
