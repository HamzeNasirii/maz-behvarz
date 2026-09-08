# Membership Architecture — Phase 28

## Domain Boundary
- **User**: Identity/Auth
- **Member**: `approval_status` (نتیجه‌ی بررسی درخواست اولیه) + `status` (چرخه‌ی کامل بعد از پذیرش)
- **MembershipPeriod**: تاریخچه‌ی دوره‌های فعال عضویت
- **MembershipStatusHistory**: تاریخچه‌ی هر تغییر status (Actor/Timestamp/Reason)
- **MembershipFee**: مستقل از Lifecycle (قانون Payment ≠ Membership)

## State Machine
DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED → ACTIVE
↓
REJECTED (پایانی)

ACTIVE → SUSPENDED → ACTIVE (reinstate) / CANCELLED
ACTIVE → EXPIRED → ACTIVE (reinstate/renew)
ACTIVE → CANCELLED (پایانی)
تمام Transitionها از تابع مرکزی `_transition()` در `apps/members/services.py` عبور
می‌کنند که مقابل جدول `ALLOWED_TRANSITIONS` اعتبارسنجی می‌شود.

## Authorization
Permission codes جدید: `membership.review`, `membership.approve`, `membership.suspend`,
`membership.reinstate`, `membership.expire`, `membership.cancel`, `membership.fee.view`,
`membership.fee.update`. همه از طریق `Authorization.can()` موجود.

## Admin Restriction
`Member.status` در Admin `readonly` است — تغییر فقط از طریق Service Layer (که
History هم ثبت می‌کند)، حتی برای Superuser.

## Known Issues
هیچ‌کدام شناخته‌شده نیست.

## Technical Debt
- Expiration خودکار (Automated Job بر اساس تاریخ) پیاده‌سازی نشد — طبق سند
  («اگر لازم نیست فقط Domain Logic آماده شود») فقط تابع `expire_membership`
  دستی موجود است.
- `membership.fee.view` Permission seed شده ولی هنوز هیچ View مصرفش نمی‌کند
  (فقط Admin) — در فاز بعدی که UI حق عضویت در Portal اضافه شود مصرف می‌شود.