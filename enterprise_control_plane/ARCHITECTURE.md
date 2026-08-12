# DataSense Enterprise Control Plane

## هدف و مرز مسئولیت

این سرویس، مرجع مرکزی سازمان، عضویت، نقش، policy، ورود فدره و رویداد ممیزی است. نرم‌افزار دسکتاپ DataSense فقط یک **Public Client** است: ورود را در مرورگر سیستم شروع می‌کند، code کوتاه‌عمر را با PKCE مبادله می‌کند و پاسخ policy را مصرف می‌کند. هیچ تصمیم مجوز امنیتی تنها بر پایهٔ UI کلاینت گرفته نمی‌شود.

## جریان ورود

Control Plane در برابر IdP سازمان نقش **SAML Service Provider** دارد. مسیر `/v1/auth/saml/{org_slug}/start` یک request ID، state و PKCE challenge ایجاد می‌کند و AuthnRequest امضاشده را به IdP می‌فرستد. ACS در `/v1/auth/saml/{org_slug}/acs` فقط Response‌ای را می‌پذیرد که با metadata و گواهی pinned آن سازمان اعتبارسنجی شود و تطابق issuer، audience، destination، recipient، `InResponseTo`، زمان و replay شناسه‌ها را داشته باشد. سپس یک authorization code یک‌بارمصرف و کوتاه‌عمر می‌سازد. Desktop آن code را همراه PKCE verifier در `/v1/auth/token` مبادله می‌کند.

## مدل امنیتی

این نمونه از SAML toolkit معتبر استفاده می‌کند؛ XML assertion هرگز با parser سفارشی یا regex پردازش نمی‌شود. metadata و signing certificates خارج از مخزن و از مسیر مدیریت‌شده تحویل می‌شوند. ذخیرهٔ transaction، authorization code و replay identifier باید در production روی Redis با TTL اتمی انجام شود. نمونهٔ توسعه‌ای `InMemoryStore` فقط برای آزمون محلی است و در startup production رد می‌شود.

توکن access، JWT امضاشده با الگوریتم RS256 است. private key باید از KMS/HSM یا secret manager دریافت شود، نه از فایل version-controlled. refresh token opaque و به‌صورت hash نگهداری می‌شود؛ هر refresh یک token جدید می‌دهد و نشست قبلی را revoke می‌کند. رمزهای عبور IdP یا assertion خام در log ذخیره نمی‌شوند.

## RBAC

هر request احراز‌شده یک `Principal` با `organization_id`، `membership_id` و permissionهای مشتق‌شده از نقش‌ها دارد. middleware هویت را resolve می‌کند؛ dependency `require_permission()` tenant binding، action و resource را بررسی کرده و allow یا deny را در audit ثبت می‌کند. roleها فقط مجموعه‌های permission هستند؛ UI authority نیست. مدل data باید `organization_id` را روی هر resource سازمانی داشته باشد.

## الگوی استقرار

سرویس پشت reverse proxy با TLS قرار می‌گیرد؛ `X-Forwarded-*` فقط از proxy مورداعتماد پذیرفته می‌شود. PostgreSQL برای دادهٔ پایدار، Redis برای TTL/replay و object storage immutable برای audit exports در نظر گرفته شده است. health endpoint فقط برای زیرساخت است و اطلاعات حساس برنمی‌گرداند. SAML production با یک کاربر Entra/Okta sandbox، signature invalid، expired assertion، destination mismatch و replay آزمایش می‌شود.

## منابع

- NIST RBAC: https://csrc.nist.gov/projects/role-based-access-control
- OASIS SAML 2.0 Profiles: https://docs.oasis-open.org/security/saml/v2.0/saml-profiles-2.0-os.pdf
- OWASP SAML Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet.html
