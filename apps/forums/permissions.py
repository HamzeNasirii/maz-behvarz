from apps.authorization.choices import AccessScopeType
from apps.authorization.services import Authorization
from apps.employment.models import EmploymentAssignment


def _user_health_house_ids(user):
    return set(
        EmploymentAssignment.objects.filter(user=user, is_active=True).values_list("health_house_id", flat=True)
    )


def can_view_forum(user, forum):
    """
    طبق قانون صریح: بهورز به فروم‌های زنجیره‌ی نسب محل‌خدمت واقعی‌اش
    دسترسی دارد (نه هر فروم هم‌سطح دیگری) — و فقط پس از تأیید کامل
    مدارک توسط دبیر/رئیس/نایب‌رئیس (نه فقط تأیید اولیه‌ی عضویت).
    """
    if user.is_superuser or user.is_staff:
        return True

    # ⚠️ گیت مخصوص فروم: تا مدارک عضو تأیید نشده، حتی اگر Bypass
    # عمومی هیئت‌مدیره فعال باشد، دسترسی فروم مسدود می‌ماند — چون این
    # محدودیت مخصوص «بهورز»هاست، نه اعضای هیئت‌مدیره.
    try:
        member = user.member_profile
        if member.documents_verified_at is None:
            return False
    except Exception:
        pass

    if Authorization._has_delegated_full_access(user):
        return True

    if forum.scope.scope_type == AccessScopeType.GLOBAL:
        return True

    forum_house_ids = set(forum.scope.get_health_house_queryset().values_list("pk", flat=True))
    user_house_ids = _user_health_house_ids(user)
    return bool(forum_house_ids & user_house_ids)


def can_post_in_forum(user, forum):
    return can_view_forum(user, forum)


def can_moderate_forum(user, forum):
    """
    مدیریت (Pin/حذف پست/کامنت) — دسترسی کامل، یا نماینده‌ی شهرستان/
    مسئولی که RoleAssignment با Scope شامل این فروم دارد.
    """
    if Authorization._has_delegated_full_access(user) or user.is_superuser:
        return True
    return Authorization.can(user, "forum.moderate", forum)