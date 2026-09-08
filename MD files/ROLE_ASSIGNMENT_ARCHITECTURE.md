# Role Assignment Architecture — Phase 29

## Domain Boundary
- `approval_status` (فاز ۱۱): تأیید/رد اولیه‌ی تخصیص به‌عنوان یک عملیات معتبر.
- `status` (فاز ۲۹): چرخه‌ی کامل عملیاتی (PROPOSED→PENDING_APPROVAL→ACTIVE→
  SUSPENDED/ENDED/REVOKED یا REJECTED/CANCELLED).
این دو مکمل هم‌اند، نه تکراری — دقیقاً مثل الگوی Membership در فاز ۲۸.

## Authorization Engine Gap Closed
قبل از این فاز، `RoleAssignment` هیچ Resolver ثبت‌شده‌ای در Registry نداشت،
یعنی `Authorization.can(user, "role.approve", assignment)` عملاً Scope را چک
نمی‌کرد. با افزودن `_role_assignment_health_houses`/`_scope_role_assignment_queryset`
در `resolvers.py`، این شکاف بسته شد.

## Scope Escalation Prevention
`_can_manage_target_scope()` در `role_lifecycle_services.py` بررسی می‌کند که
Scope هدف (مثلاً یک County) زیرمجموعه‌ی محدوده‌ی دسترسی فعلی actor باشد — از
همان `AccessScope.get_health_house_queryset()` موجود استفاده می‌کند، نه موتور
موازی.

## Role Conflict Matrix
فعلاً خالی (`ROLE_CONFLICT_MATRIX = {}`) — چون هیچ Business Rule صریحی برای
تضاد نقش‌ها وجود ندارد. Overlap به‌طور کلی مجاز است (طبق بخش ۱۴ سند).

## Known Issues
هیچ‌کدام.

## Technical Debt
- `_scope_role_assignment_queryset` به‌صورت Python-side iteration پیاده شده
  (نه Query دیتابیسی مستقیم) چون AccessScope رابطه‌ی مستقیم به HealthHouse
  ندارد. برای حجم فعلی (ده‌ها/صدها Assignment) مشکلی ندارد؛ در مقیاس بسیار
  بزرگ باید بازنویسی شود.
- Self-service پیشنهاد نقش برای عموم اعضا (نه فقط مدیران) در این فاز اضافه
  نشد — فقط از طریق کاربران دارای Permission `role.assign`.
