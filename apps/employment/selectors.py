"""
QuerySetهای گزارشی برای Employment (طبق بخش ۲۷.۶ سند). این‌ها همیشه
از خود Assignmentهای معتبر محاسبه می‌شوند، نه فیلد Denormalized —
طبق قانون ۱۰ سند اصلی («Report نباید از داده denormalized استفاده کند»).
"""

from django.db.models import Count

from .models import EmploymentAssignment


def current_employees(user=None):
    from apps.authorization.services import Authorization

    queryset = EmploymentAssignment.objects.active().select_related(
        "user", "health_house", "health_house__center"
    )
    if user is not None:
        queryset = Authorization.scope_queryset(user, queryset)
    return queryset


def historical_employees(user=None):
    from apps.authorization.services import Authorization

    queryset = EmploymentAssignment.objects.historical().select_related(
        "user", "health_house", "health_house__center"
    )
    if user is not None:
        queryset = Authorization.scope_queryset(user, queryset)
    return queryset


def users_with_multiple_active_assignments(user=None):
    from apps.authorization.services import Authorization

    queryset = EmploymentAssignment.objects.active()
    if user is not None:
        queryset = Authorization.scope_queryset(user, queryset)
    user_ids = (
        queryset.values("user_id").annotate(count=Count("id")).filter(count__gt=1).values_list("user_id", flat=True)
    )
    return queryset.filter(user_id__in=user_ids).select_related("user", "health_house")


def employees_by_health_house(health_house):
    return EmploymentAssignment.objects.active().filter(health_house=health_house).select_related("user")


def employees_by_center(center):
    return EmploymentAssignment.objects.active().filter(health_house__center=center).select_related("user")


def employees_by_network(network):
    return EmploymentAssignment.objects.active().filter(
        health_house__center__network=network
    ).select_related("user")


def employees_by_county(county):
    return EmploymentAssignment.objects.active().filter(
        health_house__center__network__county=county
    ).select_related("user")