# Architecture Decisions — Phase 01

## Django Version
Django 5.2 LTS انتخاب شد (نه آخرین نسخه 6.1) چون پشتیبانی امنیتی تا آوریل ۲۰۲۸ دارد و
برای یک سامانه سازمانی بلندمدت، ثبات LTS بر تازگی فیچرها اولویت دارد.

## Login Strategy (Open Extension Point)
فعلاً login بر پایه `username` پیش‌فرض Django باقی مانده است. تصمیم نهایی درباره
جایگزینی با شماره موبایل به فاز بعدی موکول شده؛ `CustomUserManager` به همین منظور
از قبل به‌عنوان نقطه‌ی توسعه ایجاد شده است.

## Database Strategy
Development: SQLite (فقط برای راحتی محلی).
Production: PostgreSQL (الزامی طبق قرارداد معماری).

## User ↔ Organization Decoupling
طبق قانون ۱۸ سند، هیچ FK یا OneToOne مستقیمی بین CustomUser و HealthHouse ایجاد نشده.
این رابطه در فاز بعدی توسط EmploymentAssignment مدیریت خواهد شد.

## ON DELETE Strategy
تمام FKهای سلسله‌مراتب سازمانی از PROTECT استفاده می‌کنند تا حذف تصادفی یک والد باعث
حذف زنجیره‌ای فرزندان نشود.


## Board Positions vs. RBAC Roles
پست‌های داخلی هیئت‌مدیره (رئیس، نایب‌رئیس، خزانه‌دار، دبیر، عضو) به‌عنوان RBAC Role
تعریف نمی‌شوند. این‌ها attributeهای سازمانی هستند و در گام ۱۴ (Committee/Board) با
فیلد `position` روی مدل `BoardMembership` مدیریت می‌شوند. `Role = BOARD_MEMBER` فقط
سطح دسترسی عمومی هیئت‌مدیره را کنترل می‌کند؛ اگر پستی نیاز به Permission اضافه داشته
باشد، در لایه‌ی ABAC/Policy (گام ۰۶) با قاعده‌ای بر پایه‌ی `position` اضافه می‌شود،
نه با ساخت Role جدید برای هر پست.


## Service Layer Convention
هر اپ Business Logic خودش را در `apps/<app>/services.py` نگه می‌دارد
(نه در `models.py` یا `views.py`). قرارداد:
- هر عملیات چندمرحله‌ای یک تابع مستقل با `@transaction.atomic` است.
- توابع Keyword-only آرگومان می‌گیرند (`*, member, start_date, ...`) تا
  فراخوانی صریح و خوانا بماند.
- توابعی که رکورد تاریخی می‌بندند («end_...», «transfer_...»)، هرگز
  رکورد قدیمی را حذف نمی‌کنند؛ فقط `is_active`/`end_date` را به‌روزرسانی
  می‌کنند.
- اپ‌هایی که هنوز ساخته نشده‌اند (committees, requests, ...) وقتی در
  فاز خودشان ساخته شدند، `services.py` مخصوص خود را می‌گیرند — از قبل
  فایل خالی برایشان ساخته نمی‌شود.


## Membership Application Approval
هنگام تأیید MembershipApplication، User با رمز عبور اولیه = شماره ملی ساخته می‌شود
(تصمیم صریح کاربر). ریسک امنیتی شناخته‌شده: شماره ملی محرمانه نیست؛ توصیه‌شده برای
آینده: افزودن Force Password Change در اولین ورود (هنوز پیاده‌سازی نشده).در اینده نیاز هست در اجرای فاز Notifications/SMS باید مکانیزم ارسال لینک تنظیم
رمز اولیه (یا ورود با کد یک‌بارمصرف) را اضافه کند.

## Security Hardening (Step 20)
- Production settings: HTTPS enforced (SECURE_SSL_REDIRECT, HSTS), secure cookies,
  file-upload size capped at 5MB, rotating file logging for warnings/errors.
- Public membership application form: rate-limited to 5 requests/hour per IP
  (django-ratelimit) and server-side validation of national_code (10 digits)
  and mobile_number (Iranian format) added — this was missing since Step 12.
- Document uploads restricted to pdf/jpg/jpeg/png via FileExtensionValidator.
- SECURE_HSTS_SECONDS starts at 30 days; increase only after confirming HTTPS
  works correctly in production (a wrong HSTS setting can lock out a domain).


## Rate Limiting Cache Backend
django-ratelimit به‌صورت رسمی فقط Memcached/Redis را به‌عنوان کش امن برای
شمارش اتمیک قبول می‌کند. چون نصب Redis زیرساخت اضافه‌ای است که در این فاز
پیش‌بینی نشده، از DatabaseCache استفاده شده و هشدارهای E003/W001 آگاهانه
خاموش شده‌اند (SILENCED_SYSTEM_CHECKS). ریسک پذیرفته‌شده: تحت بار همزمان
بسیار سنگین، شمارش نرخ ممکن است کمی نادقیق باشد — نه یک آسیب‌پذیری امنیتی
حیاتی. اگر مقیاس واقعی سایت بالا رفت، به Redis (django-redis) مهاجرت شود.