from django.db import transaction

from .models import RoleAssignment


@transaction.atomic
def transfer_role_assignment(
    *, user, old_assignment, new_role, new_access_scope,
    effective_date, assigned_by=None, reason=""
):
    """
    تغییر نقش یا محدوده‌ی دسترسی یک کاربر بدون حذف تاریخچه‌ی
    RoleAssignment قبلی.
    """
    old_assignment.end_date = effective_date
    old_assignment.is_active = False
    old_assignment.save(update_fields=["end_date", "is_active", "updated_at"])

    return RoleAssignment.objects.create(
        user=user,
        role=new_role,
        access_scope=new_access_scope,
        start_date=effective_date,
        is_active=True,
        assigned_by=assigned_by,
        reason=reason,
    )

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from .choices import ApprovalStatus
from .services import Authorization


@transaction.atomic
def approve_role_assignment(*, role_assignment, approved_by):
    if not Authorization.can(approved_by, "role.approve", role_assignment):
        raise PermissionDenied("این کاربر مجوز تأیید تخصیص نقش را ندارد.")
    if role_assignment.assigned_by_id and role_assignment.assigned_by_id == approved_by.id:
        raise PermissionDenied("ثبت‌کننده‌ی تخصیص نقش نمی‌تواند تأییدکننده‌ی همان درخواست باشد.")

    role_assignment.approval_status = ApprovalStatus.APPROVED
    role_assignment.approved_by = approved_by
    role_assignment.approved_at = timezone.now()
    role_assignment.rejection_reason = ""
    role_assignment.save(
        update_fields=["approval_status", "approved_by", "approved_at", "rejection_reason", "updated_at"]
    )
    return role_assignment


@transaction.atomic
def reject_role_assignment(*, role_assignment, rejected_by, reason):
    if not Authorization.can(rejected_by, "role.approve", role_assignment):
        raise PermissionDenied("این کاربر مجوز رد تخصیص نقش را ندارد.")
    if role_assignment.assigned_by_id and role_assignment.assigned_by_id == rejected_by.id:
        raise PermissionDenied("ثبت‌کننده‌ی تخصیص نقش نمی‌تواند رد‌کننده‌ی همان درخواست باشد.")

    role_assignment.approval_status = ApprovalStatus.REJECTED
    role_assignment.approved_by = rejected_by
    role_assignment.approved_at = timezone.now()
    role_assignment.rejection_reason = reason
    role_assignment.save(
        update_fields=["approval_status", "approved_by", "approved_at", "rejection_reason", "updated_at"]
    )
    return role_assignment