from .choices import RoleAssignmentStatus
from .models import RoleAssignment


def current_role_assignments(user):
    return RoleAssignment.objects.for_user(user).active().select_related("role", "access_scope")


def role_assignment_history(user):
    return RoleAssignment.objects.for_user(user).select_related("role", "access_scope").order_by("-start_date")


def pending_role_assignments(user):
    """مدیریتی — Scope-aware از طریق scope_queryset (Resolver بالا)."""
    from .services import Authorization

    queryset = RoleAssignment.objects.filter(
        status=RoleAssignmentStatus.PENDING_APPROVAL
    ).select_related("user", "role", "access_scope")
    return Authorization.scope_queryset(user, queryset)


def assignments_by_role(role):
    return RoleAssignment.objects.filter(role=role).active().select_related("user", "access_scope")


def assignments_by_scope(access_scope):
    return RoleAssignment.objects.filter(access_scope=access_scope).active().select_related("user", "role")

def county_representatives(county):
    """نمایندگان فعال یک شهرستان مشخص — از RoleAssignment موجود."""
    return RoleAssignment.objects.filter(
        role__code="COUNTY_REPRESENTATIVE", access_scope__county=county,
    ).active().select_related("user", "access_scope")


def public_representatives():
    """
    طبق بخش ۲۱ سند: فقط نمایندگانی که is_public_visible=True دارند،
    نه اطلاعات خصوصی.
    """
    return RoleAssignment.objects.filter(
        role__code="COUNTY_REPRESENTATIVE", is_public_visible=True,
    ).active().select_related("user", "access_scope__county")