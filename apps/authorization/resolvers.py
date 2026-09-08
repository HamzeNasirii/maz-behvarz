from apps.employment.models import EmploymentAssignment
from apps.members.models import Member
from apps.organization.models import HealthHouse

from .choices import AccessScopeType
from .registry import register_health_house_resolver, register_queryset_scope_resolver


def _member_health_houses(member):
    return HealthHouse.objects.filter(
        employment_assignments__user=member.user,
        employment_assignments__is_active=True,
    ).distinct()


def _employment_assignment_health_houses(assignment):
    return HealthHouse.objects.filter(pk=assignment.health_house_id)


def _scope_member_queryset(queryset, house_ids):
    return queryset.filter(
        user__employment_assignments__health_house_id__in=house_ids,
        user__employment_assignments__is_active=True,
    ).distinct()


def _scope_employment_queryset(queryset, house_ids):
    return queryset.filter(health_house_id__in=house_ids)


def _role_assignment_health_houses(role_assignment):
    """
    Scope خود تخصیص نقش، از طریق AccessScope متصل‌شده به آن محاسبه
    می‌شود. GLOBAL/SELF/COMMITTEE هیچ Containment سازمانی ندارند
    (طبق طراحی AccessScope در فاز ۰۵)، پس خالی برمی‌گردد.
    """
    return role_assignment.access_scope.get_health_house_queryset()


def _scope_role_assignment_queryset(queryset, house_ids):
    """
    چون AccessScope رابطه‌ی مستقیم FK به HealthHouse ندارد (چندسطحی
    است)، Containment باید به‌صورت محاسباتی بررسی شود. برای حجم
    مدیریتی معمول (نه میلیونی) این روش قابل قبول است؛ در صورت رشد
    مقیاس، باید به Query سطح دیتابیس بازنویسی شود (مستند در بخش
    Technical Debt).
    """
    house_ids_set = set(house_ids)
    matching_ids = []
    for assignment in queryset.select_related("access_scope"):
        if assignment.access_scope.scope_type == AccessScopeType.GLOBAL:
            matching_ids.append(assignment.pk)
            continue
        assignment_houses = set(
            assignment.access_scope.get_health_house_queryset().values_list("pk", flat=True)
        )
        if assignment_houses & house_ids_set:
            matching_ids.append(assignment.pk)
    return queryset.filter(pk__in=matching_ids)


def register_all():
    from .models import RoleAssignment

    register_health_house_resolver(Member, _member_health_houses)
    register_health_house_resolver(EmploymentAssignment, _employment_assignment_health_houses)
    register_health_house_resolver(RoleAssignment, _role_assignment_health_houses)

    register_queryset_scope_resolver(Member, _scope_member_queryset)
    register_queryset_scope_resolver(EmploymentAssignment, _scope_employment_queryset)
    register_queryset_scope_resolver(RoleAssignment, _scope_role_assignment_queryset)