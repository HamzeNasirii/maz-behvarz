def get_accessible_province_ids(user):
    """
    None یعنی دسترسی کامل به همه‌ی استان‌ها (فقط Staff/Superuser واقعی).
    در غیر این صورت، مجموعه‌ی شناسه‌ی استان‌هایی که کاربر واقعاً از
    طریق RoleAssignment سطح‌استان به آن‌ها دسترسی دارد — این تابع
    مرجع مشترک برای هر بخشی از پروژه است که نیاز به «کدام استان‌ها
    برای این کاربر مجازند» دارد (گزارش‌ها، مدیریت سازمانی، ...).
    """
    if user.is_superuser or user.is_staff:
        return None

    from .choices import AccessScopeType
    from .services import Authorization

    province_ids = set()
    for assignment in Authorization.get_active_role_assignments(user).select_related("access_scope"):
        scope = assignment.access_scope
        if scope.scope_type == AccessScopeType.PROVINCE and scope.province_id:
            province_ids.add(scope.province_id)
    return province_ids


def get_access_scope_province_id(access_scope):
    """
    استخراج شناسه‌ی استان مربوط به یک AccessScope، صرف‌نظر از سطح آن
    (استان/شهرستان/شبکه/مرکز/خانه). برای GLOBAL و COMMITTEE (که مفهوم
    استان مستقیم ندارند)، None برمی‌گرداند — یعنی «قابل تشخیص نیست»،
    که در _require_own_province به‌عنوان «غیرمجاز برای غیر ادمین»
    تفسیر می‌شود (محافظه‌کارانه، نه بازگشایی ناخواسته).
    """
    from .choices import AccessScopeType

    scope_type = access_scope.scope_type
    if scope_type == AccessScopeType.PROVINCE:
        return access_scope.province_id
    if scope_type == AccessScopeType.COUNTY and access_scope.county_id:
        return access_scope.county.province_id
    if scope_type == AccessScopeType.NETWORK and access_scope.network_id:
        return access_scope.network.county.province_id
    if scope_type == AccessScopeType.CENTER and access_scope.center_id:
        return access_scope.center.network.county.province_id
    if scope_type == AccessScopeType.HOUSE and access_scope.house_id:
        return access_scope.house.center.network.county.province_id
    return None