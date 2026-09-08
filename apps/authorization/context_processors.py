from apps.board.permissions import is_board_leadership

from .choices import ApprovalStatus


def pending_dashboard_flag(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    can_view = user.is_superuser or user.is_staff or is_board_leadership(user)
    context = {"can_view_pending_dashboard": can_view}

    if can_view:
        context["pending_requests_count"] = _count_all_pending(user)

    return context


def _count_all_pending(user):
    """
    همان چهار شمارشی که در admin_dashboard.py محاسبه می‌شود — این‌بار
    Scope-aware، دقیقاً با همان منطقی که در pending_views.py برای
    نمایش خود لیست‌ها استفاده می‌شود؛ تا این شمارنده هرگز موارد خارج
    از محدوده‌ی دسترسی واقعی کاربر را نشان ندهد.
    """
    from .services import Authorization
    from apps.employment.models import EmploymentAssignment
    from apps.members.models import Member
    from apps.website.models import MembershipApplication

    from .models import RoleAssignment

    pending_applications = Authorization.scope_queryset(
        user, MembershipApplication.objects.filter(status=ApprovalStatus.PENDING)
    ).count()

    pending_members = Member.objects.for_user(user).filter(
        approval_status=ApprovalStatus.PENDING
    ).count()

    pending_employment = EmploymentAssignment.objects.for_user(user).filter(
        approval_status=ApprovalStatus.PENDING
    ).count()

    pending_roles = Authorization.scope_queryset(
        user, RoleAssignment.objects.filter(approval_status=ApprovalStatus.PENDING)
    ).count()

    return pending_applications + pending_members + pending_employment + pending_roles