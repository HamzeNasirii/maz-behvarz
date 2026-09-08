# Committee Management Architecture — Phase 30

## Domain Boundary
- **Committee**: Entity سازمانی مستقل، با Lifecycle خودش (DRAFT→ACTIVE→SUSPENDED→ENDED→ARCHIVED).
- **CommitteeMembership**: رابطه‌ی ساده‌ی عضویت (از فاز ۱۴، تاریخی از قبل).
- **Chair/Secretary**: **فیلد نیستند** — از `RoleAssignment` با `access_scope.scope_type=COMMITTEE`
  و `access_scope.committee=<Committee>` ساخته می‌شوند (Role codes: `COMMITTEE_MANAGER` برای
  Chair، `COMMITTEE_SECRETARY` جدید برای دبیر).

## AccessScope Extension
`AccessScope.committee` (FK جدید) اضافه شد تا `scope_type=COMMITTEE` بتواند به یک کمیته‌ی
مشخص Containment داشته باشد — قبل از این فاز، این نوع Scope هیچ FK نداشت.

## Committee's Own Scope vs RoleAssignment Scope
`Committee.scope` (FK به AccessScope، معمولاً PROVINCE/COUNTY) نشان می‌دهد خود کمیته در
چه محدوده‌ی جغرافیایی‌ای تعریف شده — این مستقل از Scope هر RoleAssignment مربوط به آن
کمیته است (طبق مثال بخش ۱۰ سند: عضویت در شهرستان A، ولی مسئولیت کمیته در سطح استان).

## Authorization (بدون موتور موازی)
`apps/committees/authorization.py` فقط از `Authorization.has_permission_code()` و
`AccessScope` موجود استفاده می‌کند. چون Committee به HealthHouse وصل نیست، Resolver
خانه‌بهداشت-محور موجود (`registry.py`) برایش کاربرد ندارد؛ به‌جایش
`_geographic_scope_contains()` مقایسه‌ی مستقیم Province/County را انجام می‌دهد.

## Known Issues
هیچ‌کدام.

## Technical Debt
- `committees_for_user()` با Python-side iteration پیاده شده (نه Query دیتابیسی) —
  برای تعداد کم کمیته مناسب است؛ در مقیاس بزرگ باید بازنویسی شود.
- Committee Membership فاقد Workflow چندمرحله‌ای (Proposed→Approved) است — طبق بخش ۱۴
  سند («اگر مشابه در RoleAssignment وجود دارد Reuse کن»، ولی برای سادگی عضویت ساده
  نگه داشته شد چون خود Chair/Secretary از طریق RoleAssignment که Workflow کامل دارد
  مدیریت می‌شود).
