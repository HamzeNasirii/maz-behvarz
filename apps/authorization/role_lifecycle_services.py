from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.board.permissions import is_role_decision_authority


from .choices import ALLOWED_ROLE_TRANSITIONS, AccessScopeType, RoleAssignmentStatus
from .models import RoleAssignment, RoleAssignmentStatusHistory
from .registry import get_object_health_houses
from .services import Authorization

@transaction.atomic
def approve_role_assignment_lifecycle(*, assignment, actor):
    if not _can_decide_role_assignment(actor, assignment):
        raise PermissionDenied("فقط رئیس، نایب‌رئیس یا دبیر انجمن می‌توانند این تخصیص نقش را تأیید کنند.")
    is_admin = actor.is_superuser or actor.is_staff
    if assignment.assigned_by_id == actor.id and not is_admin:
        raise PermissionDenied("پیشنهاددهنده نمی‌تواند تأییدکننده‌ی همان تخصیص باشد.")
    return _transition(assignment=assignment, new_status=RoleAssignmentStatus.ACTIVE, actor=actor)


def _can_manage_target_scope(actor, target_scope):
    """
    بررسی می‌کند آیا actor از طریق نقش‌های فعال خودش، به محدوده‌ای
    که target_scope نشان می‌دهد (یا محدوده‌ی وسیع‌تری شامل آن)
    دسترسی دارد — با استفاده از همان AccessScope.get_health_house_queryset()
    موجود، نه یک موتور موازی.
    """
    if actor.is_superuser:
        return True

    if target_scope.scope_type == AccessScopeType.GLOBAL:
        return Authorization.get_active_role_assignments(actor).filter(
            access_scope__scope_type=AccessScopeType.GLOBAL
        ).exists()

    if target_scope.scope_type in (AccessScopeType.SELF, AccessScopeType.COMMITTEE):
        # این دو نوع Scope فعلاً Containment سازمانی ندارند (فاز ۰۵)
        return True

    target_houses = set(target_scope.get_health_house_queryset().values_list("pk", flat=True))
    if not target_houses:
        return True

    for assignment in Authorization.get_active_role_assignments(actor).select_related("access_scope"):
        if assignment.access_scope.scope_type == AccessScopeType.GLOBAL:
            return True
        assigner_houses = set(
            assignment.access_scope.get_health_house_queryset().values_list("pk", flat=True)
        )
        if target_houses.issubset(assigner_houses):
            return True
    return False


def _transition(*, assignment, new_status, actor, reason="", comment=""):
    allowed = ALLOWED_ROLE_TRANSITIONS.get(assignment.status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"تغییر وضعیت از «{assignment.get_status_display()}» به این وضعیت مجاز نیست."
        )

    RoleAssignmentStatusHistory.objects.create(
        role_assignment=assignment, previous_status=assignment.status, new_status=new_status,
        actor=actor, reason=reason, comment=comment,
    )
    assignment.status = new_status
    assignment.is_active = new_status == RoleAssignmentStatus.ACTIVE
    assignment.save(update_fields=["status", "is_active", "updated_at"])
    return assignment


@transaction.atomic
def assign_role(*, assigned_by, user, role, access_scope, start_date, end_date=None, reason=""):
    if not Authorization.has_permission_code(assigned_by, "role.assign"):
        raise PermissionDenied("این کاربر مجوز تخصیص نقش را ندارد.")

    if assigned_by.id == user.id and not assigned_by.is_superuser:
        raise PermissionDenied("کاربر نمی‌تواند برای خودش نقش ایجاد کند.")

    if not _can_manage_target_scope(assigned_by, access_scope):
        raise PermissionDenied("این کاربر مجاز به تخصیص نقش در این محدوده‌ی دسترسی نیست.")

    assignment = RoleAssignment.objects.create(
        user=user, role=role, access_scope=access_scope, start_date=start_date, end_date=end_date,
        assigned_by=assigned_by, reason=reason,
        status=RoleAssignmentStatus.PROPOSED, is_active=False,
    )
    RoleAssignmentStatusHistory.objects.create(
        role_assignment=assignment, previous_status="", new_status=RoleAssignmentStatus.PROPOSED,
        actor=assigned_by, reason=reason,
    )
    return assignment


@transaction.atomic
def submit_role_assignment_for_approval(*, assignment, actor):
    if assignment.assigned_by_id != actor.id and not Authorization.has_permission_code(actor, "role.assign"):
        raise PermissionDenied("این کاربر مجوز ارسال این تخصیص برای بررسی را ندارد.")
    return _transition(assignment=assignment, new_status=RoleAssignmentStatus.PENDING_APPROVAL, actor=actor)


@transaction.atomic
def _can_decide_role_assignment(actor, assignment):
    """
    طبق تصمیم صریح: تصمیم نهایی روی تخصیص نقش فقط برای رئیس/نایب‌رئیس/
    دبیر/Staff/Superuser مجاز است — نه برای «هر» عضو هیئت‌مدیره (که
    Bypass عمومی سیستم به آن‌ها می‌دهد). برای کاربران غیرهیئت‌مدیره
    (مثلاً یک مدیر شهرستانی با Permission واقعی)، مسیر RBAC معمولی
    (بدون Bypass هیئت‌مدیره) همچنان معتبر است.
    """
    if actor.is_superuser or actor.is_staff:
        return True
    if is_role_decision_authority(actor):
        return True

    # مسیر RBAC واقعی — بدون استفاده از Bypass عمومی هیئت‌مدیره، تا
    # عضو ساده‌ی هیئت‌مدیره از این راه هم نتواند عبور کند.
    if "role.approve" not in Authorization.get_permission_codes(actor):
        return False

    houses = get_object_health_houses(assignment)
    if houses is None or not houses.exists():
        return True
    house_ids = set(houses.values_list("pk", flat=True))
    for role_assignment in Authorization.get_active_role_assignments(actor).select_related("access_scope"):
        assigner_houses = set(
            role_assignment.access_scope.get_health_house_queryset().values_list("pk", flat=True)
        )
        if house_ids & assigner_houses:
            return True
    return False

@transaction.atomic
def reject_role_assignment_lifecycle(*, assignment, actor, reason):
    if not reason:
        raise ValidationError("ثبت دلیل رد الزامی است.")
    if not _can_decide_role_assignment(actor, assignment):
        raise PermissionDenied("فقط رئیس، نایب‌رئیس یا دبیر انجمن می‌توانند این تخصیص نقش را رد کنند.")
    return _transition(assignment=assignment, new_status=RoleAssignmentStatus.REJECTED, actor=actor, reason=reason)


@transaction.atomic
def suspend_role_assignment(*, assignment, actor, reason):
    if not reason:
        raise ValidationError("ثبت دلیل تعلیق الزامی است.")
    if not Authorization.can(actor, "role.revoke", assignment):
        raise PermissionDenied("این کاربر مجوز تعلیق این تخصیص نقش را ندارد.")
    return _transition(assignment=assignment, new_status=RoleAssignmentStatus.SUSPENDED, actor=actor, reason=reason)


@transaction.atomic
def reactivate_role_assignment(*, assignment, actor, reason=""):
    if not Authorization.can(actor, "role.approve", assignment):
        raise PermissionDenied("این کاربر مجوز فعال‌سازی مجدد این تخصیص نقش را ندارد.")
    return _transition(assignment=assignment, new_status=RoleAssignmentStatus.ACTIVE, actor=actor, reason=reason)


@transaction.atomic
def end_role_assignment(*, assignment, actor, end_date, reason=""):
    if not Authorization.can(actor, "role.revoke", assignment):
        raise PermissionDenied("این کاربر مجوز پایان‌دادن به این تخصیص نقش را ندارد.")
    assignment.end_date = end_date
    _transition(assignment=assignment, new_status=RoleAssignmentStatus.ENDED, actor=actor, reason=reason)
    return assignment


@transaction.atomic
def revoke_role_assignment(*, assignment, actor, reason):
    if not reason:
        raise ValidationError("ثبت دلیل لغو اجباری الزامی است.")
    if not Authorization.can(actor, "role.revoke", assignment):
        raise PermissionDenied("این کاربر مجوز لغو این تخصیص نقش را ندارد.")
    assignment.end_date = timezone.localdate()
    _transition(assignment=assignment, new_status=RoleAssignmentStatus.REVOKED, actor=actor, reason=reason)
    return assignment


@transaction.atomic
def cancel_role_assignment(*, assignment, actor, reason=""):
    if assignment.assigned_by_id != actor.id and not Authorization.can(actor, "role.revoke", assignment):
        raise PermissionDenied("این کاربر مجوز لغو این تخصیص پیشنهادی را ندارد.")
    return _transition(assignment=assignment, new_status=RoleAssignmentStatus.CANCELLED, actor=actor, reason=reason)