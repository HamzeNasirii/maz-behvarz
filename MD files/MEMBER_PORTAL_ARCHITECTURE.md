# Member Portal Architecture — Phase 26

## Authentication
Django built-in `LoginView`/`PasswordReset*View`. Login با `username` (بدون تغییر،
طبق تصمیم باز فاز ۰۱). Password Reset با `console` Email Backend در Development
(ایمیل واقعی ارسال نمی‌شود، فقط در ترمینال چاپ می‌شود) — SMTP واقعی به فاز
Notification Engine موکول شده است.

## User ≠ Member ≠ Behvarz
- **User** (`CustomUser`): فقط Identity/Authentication.
- **Member** (`apps.members.Member`): عضویت انجمن، وضعیت تأیید.
- **Behvarz/Employment** (`apps.employment.EmploymentAssignment`): هویت شغلی، چندمحله.
این سه هرگز در یک مدل ادغام نشده‌اند.

## URL Architecture (بدون تغییر نسبت به فازهای قبل)

/portal/ ← Dashboard
/portal/employment-history/
/portal/profile/
/portal/profile/edit/ ← جدید در این فاز

هیچ‌کدام از ID در URL استفاده نمی‌کنند — مالکیت همیشه از طریق `request.user` تضمین می‌شود.

## Authorization Boundary
Dashboard/Profile به‌صورت ذاتی Scope-safe‌اند (چون فقط `request.user` را می‌خوانند).
Employment/Role Summary از طریق `EmploymentAssignment.objects.for_user()` و
`RoleAssignment.objects.for_user()` — نه `Authorization.scope_queryset()` — چون این‌ها
همیشه داده‌ی خود کاربر است، نه داده‌ی Scope شده برای مدیریت دیگران.

## Profile Edit Restriction
فرم `ProfileEditForm` فقط `first_name`, `last_name`, `email` دارد. تزریق فیلدهای
`role`/`health_house`/`access_scope` از طریق POST مستقیم بی‌اثر است چون ModelForm
فقط فیلدهای تعریف‌شده در `Meta.fields` را می‌پذیرد — این با تست
`RoleEscalationTests`/`EmploymentManipulationTests` تثبیت شده است.

## Navigation
آیتم‌های بدون Backend («نقش‌ها»، «اعلان‌ها»، «اسناد») به‌صورت متن غیرفعال
(Coming Soon) نمایش داده می‌شوند، نه لینک شکسته.

## Known Limitations / Technical Debt
- Password Reset Email فقط Console (نه SMTP واقعی).
- «نقش‌ها»/«اعلان‌ها»/«اسناد» در Sidebar فعلاً Placeholder‌اند (Backend در فازهای بعدی).
- Avatar پیاده‌سازی نشد (در سند به‌عنوان اختیاری ذکر شده بود).