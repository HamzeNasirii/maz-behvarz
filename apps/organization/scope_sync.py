"""
همگام‌سازی خودکار AccessScope با ساختار سازمانی — هر بار یک بخش
سازمانی (استان/شهرستان/شبکه/مرکز/خانه‌بهداشت) ایجاد می‌شود، یک
AccessScope متناظر (اگر از قبل نبود) خودکار ساخته می‌شود. طبق قانون
صریح: هرگز محدوده‌ی تکراری ایجاد نمی‌شود (get_or_create).
"""

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope

LEVEL_TO_SCOPE_TYPE = {
    "province": AccessScopeType.PROVINCE,
    "county": AccessScopeType.COUNTY,
    "network": AccessScopeType.NETWORK,
    "center": AccessScopeType.CENTER,
    "house": AccessScopeType.HOUSE,
}

LEVEL_TO_FIELD_NAME = {
    "province": "province",
    "county": "county",
    "network": "network",
    "center": "center",
    "house": "house",
}


def ensure_access_scope_for(level, instance):
    """
    برای رکورد سازمانی داده‌شده، یک AccessScope متناظر (اگر وجود
    نداشت) می‌سازد و برمی‌گرداند. Idempotent است — فراخوانی چندباره
    هرگز رکورد تکراری نمی‌سازد.
    """
    scope_type = LEVEL_TO_SCOPE_TYPE[level]
    field_name = LEVEL_TO_FIELD_NAME[level]
    scope, _ = AccessScope.objects.get_or_create(
        scope_type=scope_type, **{field_name: instance}
    )
    return scope


FORUM_ELIGIBLE_LEVELS = ("province", "county", "network", "center")  # عمداً "house" ندارد

LEVEL_FORUM_LABELS = {
    "province": "استان",
    "county": "شهرستان",
    "network": "شبکه بهداشت و درمان",
    "center": "مرکز خدمات جامع سلامت",
}


def ensure_forum_for(level, instance, access_scope):
    """
    برای هر گره‌ی سازمانی (به‌جز خانه‌بهداشت)، یک فروم متناظر (اگر
    وجود نداشت) خودکار می‌سازد — طبق تصمیم صریح کاربر برای کاهش کار
    دستی. Idempotent است (get_or_create).
    """
    from apps.forums.models import Forum

    if level not in FORUM_ELIGIBLE_LEVELS:
        return None

    label = LEVEL_FORUM_LABELS[level]
    default_name = f"فروم {label} {instance.name}"

    forum, _ = Forum.objects.get_or_create(
        scope=access_scope, defaults={"name": default_name},
    )
    return forum