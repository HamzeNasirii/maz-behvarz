from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.board.permissions import is_board_leadership

from .services import (
    board_and_committee_statistics,
    county_coverage_statistics,
    employment_statistics,
    extended_admin_statistics,
    member_statistics,
)
from django.shortcuts import render


def _can_view_reports(user):
    return user.is_superuser or user.is_staff or is_board_leadership(user)


@login_required
def reports_dashboard_view(request):
    if not _can_view_reports(request.user):
        raise PermissionDenied("شما مجوز مشاهده‌ی این صفحه را ندارید.")

    context = {
        "member_stats": member_statistics(request.user),
        "employment_stats": employment_statistics(request.user),
        "board_committee_stats": board_and_committee_statistics(request.user),
        "county_coverage": county_coverage_statistics(request.user),
        "extended_stats": extended_admin_statistics(request.user),
    }
    return render(request, "reports/dashboard.html", context)