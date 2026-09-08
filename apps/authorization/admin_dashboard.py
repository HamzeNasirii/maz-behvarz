from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from apps.board.permissions import is_board_leadership

from .choices import ApprovalStatus
from .models import RoleAssignment
from .services import Authorization


def _can_view_pending_dashboard(user):
    return user.is_superuser or user.is_staff or is_board_leadership(user)


@login_required
def pending_requests_view(request):
    if not _can_view_pending_dashboard(request.user):
        raise PermissionDenied("شما مجوز مشاهده‌ی این صفحه را ندارید.")

    from apps.employment.models import EmploymentAssignment
    from apps.members.models import Member
    from apps.website.models import MembershipApplication

    context = {
        "pending_applications": Authorization.scope_queryset(
            request.user, MembershipApplication.objects.filter(status=ApprovalStatus.PENDING)
        ).count(),
        "pending_members": Member.objects.for_user(request.user).filter(
            approval_status=ApprovalStatus.PENDING
        ).count(),
        "pending_employment": EmploymentAssignment.objects.for_user(request.user).filter(
            approval_status=ApprovalStatus.PENDING
        ).count(),
        "pending_roles": Authorization.scope_queryset(
            request.user, RoleAssignment.objects.filter(approval_status=ApprovalStatus.PENDING)
        ).count(),
    }
    return render(request, "authorization/pending_dashboard.html", context)