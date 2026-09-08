"""
منطق Domain-specific برای Authorization کمیته‌ها. هیچ موتور Authorization
موازی ساخته نشده — فقط از Authorization.has_permission_code() و
AccessScope موجود استفاده می‌شود، چون Committee (برخلاف Member/
EmploymentAssignment) به HealthHouse وصل نیست و Resolver خانه‌بهداشت-محور
موجود برایش معنا ندارد.
"""

from apps.authorization.choices import AccessScopeType
from apps.authorization.services import Authorization


def _geographic_scope_contains(outer, inner):
    """
    آیا Scope جغرافیایی outer شامل Scope جغرافیایی inner است؟ فقط
    PROVINCE/COUNTY را پوشش می‌دهد — چون Committee.scope طبق طراحی
    فقط این دو سطح را پشتیبانی می‌کند (بخش ۹ سند).
    """
    if outer.scope_type == AccessScopeType.GLOBAL:
        return True
    if outer.scope_type == AccessScopeType.PROVINCE:
        if inner.scope_type == AccessScopeType.PROVINCE:
            return inner.province_id == outer.province_id
        if inner.scope_type == AccessScopeType.COUNTY:
            return inner.county.province_id == outer.province_id
        return False
    if outer.scope_type == AccessScopeType.COUNTY:
        return inner.scope_type == AccessScopeType.COUNTY and inner.county_id == outer.county_id
    return False


def can_manage_committee(user, committee, permission_code):
    if user.is_superuser or user.is_staff:
        return True
    if not Authorization.has_permission_code(user, permission_code):
        return False

    for assignment in Authorization.get_active_role_assignments(user).select_related("access_scope"):
        scope = assignment.access_scope
        if scope.scope_type == AccessScopeType.GLOBAL:
            return True
        if scope.scope_type == AccessScopeType.COMMITTEE and scope.committee_id == committee.id:
            return True
        if committee.scope_id and scope.scope_type in (AccessScopeType.PROVINCE, AccessScopeType.COUNTY):
            if _geographic_scope_contains(scope, committee.scope):
                return True
    return False


def committees_for_user(user, queryset=None):
    from .models import Committee

    if queryset is None:
        queryset = Committee.objects.all()
    if user.is_superuser or user.is_staff:
        return queryset
    if not Authorization.has_permission_code(user, "committee.view"):
        return queryset.none()

    accessible_ids = [c.pk for c in queryset if can_manage_committee(user, c, "committee.view")]
    return queryset.filter(pk__in=accessible_ids)