# Board & Representative Architecture — Phase 31

## Board Period vs BoardMembership.position
`Board` (جدید) دوره را نمایندگی می‌کند؛ `BoardMembership.position` (از فاز ۱۴، بدون
تغییر) سمت فرد را مشخص می‌کند — این‌ها دو Domain مستقل‌اند (طبق بخش ۳ سند).

## Assumption مهم: Uniqueness Constraints بدون board
`uniq_active_board_membership_per_user` و `uniq_active_unique_board_position` عمداً
بدون فیلد `board` باقی مانده‌اند تا رفتار Regression-tested فاز ۱۴ («هم‌زمان فقط یک
رئیس فعال در کل سیستم») نشکند. یعنی همچنان در هر لحظه، فارغ از این‌که به کدام Board
period متصل باشند، فقط یک رئیس/نایب‌رئیس/خزانه‌دار/دبیر فعال مجاز است. این با واقعیت
عملی همخوان است چون در هر لحظه فقط یک دوره باید ACTIVE باشد.

## Representative (County/Province)
مدل جدیدی ساخته نشد — از `RoleAssignment(role.code=COUNTY_REPRESENTATIVE, access_scope=COUNTY)`
موجود استفاده می‌شود. فیلد جدید `RoleAssignment.is_public_visible` (پیش‌فرض False)
اضافه شد تا انتشار عمومی نماینده مستقل از انتشار عمومی داده‌های خصوصی او باشد.

## Public Visibility
`Board.is_public_visible` و `RoleAssignment.is_public_visible` هر دو پیش‌فرض False —
هیچ داده‌ی موجودی به‌طور خودکار عمومی نشد.

## Known Issues
هیچ‌کدام.

## Technical Debt
- چون uniqueness هنوز per-board نیست، اگر در آینده واقعاً چند Board هم‌زمان ACTIVE
  لازم شد (که فعلاً پیش‌بینی نشده)، این Constraintها باید بازبینی شوند.
- Public Board Page موجود (`apps/public_content/views.py::board_view`) هنوز بر اساس
  دوره فیلتر نمی‌کند — همه‌ی BoardMembershipهای `is_active=True و is_public_visible=True`
  را نشان می‌دهد صرف‌نظر از Board period؛ این برای وضعیت فعلی (یک دوره‌ی فعال) درست
  کار می‌کند، ولی برای فاز‌های بعدی که چند دوره را کنار هم می‌خواهیم مقایسه کنیم،
  باید فیلتر `board=current_board()` اضافه شود.
