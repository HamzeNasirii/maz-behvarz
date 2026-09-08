from django.db import transaction

from .models import EmploymentAssignment
from apps.notifications.choices import NotificationType
from apps.notifications.services import send_notification

@transaction.atomic
def transfer_primary_employment(
    *, user, new_health_house, effective_date,
    employment_type=None, assigned_by=None, reason=""
):
    """
    جابه‌جایی محل خدمت اصلی یک کاربر بدون حذف تاریخچه.

    رکورد EmploymentAssignment قبلی (is_primary=True, is_active=True)
    هرگز حذف نمی‌شود؛ end_date و is_active آن به‌روزرسانی می‌شود و یک
    رکورد جدید برای محل خدمت جدید ایجاد می‌شود.
    """
    previous = (
        EmploymentAssignment.objects.for_user(user)
        .active()
        .filter(is_primary=True)
        .select_for_update()
        .first()
    )

    if previous is not None:
        previous.end_date = effective_date
        previous.is_active = False
        previous.save(update_fields=["end_date", "is_active", "updated_at"])

    new_assignment = EmploymentAssignment.objects.create(
        user=user,
        health_house=new_health_house,
        employment_type=employment_type or (previous.employment_type if previous else "behvarz"),
        start_date=effective_date,
        is_active=True,
        is_primary=True,
        assigned_by=assigned_by,
        reason=reason,
    )
    return new_assignment

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.authorization.choices import ApprovalStatus
from apps.authorization.services import Authorization


@transaction.atomic
def approve_employment_transfer(*, assignment, approved_by):
    if not Authorization.can(approved_by, "employment.approve", assignment):
        raise PermissionDenied("این کاربر مجوز تأیید جابه‌جایی محل خدمت را ندارد.")
    if assignment.assigned_by_id and assignment.assigned_by_id == approved_by.id:
        raise PermissionDenied("ثبت‌کننده‌ی تخصیص نمی‌تواند تأییدکننده‌ی همان درخواست باشد.")

    assignment.approval_status = ApprovalStatus.APPROVED
    assignment.approved_by = approved_by
    assignment.approved_at = timezone.now()
    assignment.rejection_reason = ""
    assignment.save(update_fields=["approval_status", "approved_by", "approved_at", "rejection_reason", "updated_at"])

    send_notification(
        recipient=assignment.user,
        notification_type=NotificationType.EMPLOYMENT_APPROVED,
        title="جابه‌جایی محل خدمت تأیید شد",
        message=f"جابه‌جایی شما به {assignment.health_house.name} تأیید شد.",
        related_object=assignment,
    )

    return assignment


@transaction.atomic
def reject_employment_transfer(*, assignment, rejected_by, reason):
    if not Authorization.can(rejected_by, "employment.approve", assignment):
        raise PermissionDenied("این کاربر مجوز رد جابه‌جایی محل خدمت را ندارد.")
    if assignment.assigned_by_id and assignment.assigned_by_id == rejected_by.id:
        raise PermissionDenied("ثبت‌کننده‌ی تخصیص نمی‌تواند رد‌کننده‌ی همان درخواست باشد.")

    assignment.approval_status = ApprovalStatus.REJECTED
    assignment.approved_by = rejected_by
    assignment.approved_at = timezone.now()
    assignment.rejection_reason = reason
    assignment.save(update_fields=["approval_status", "approved_by", "approved_at", "rejection_reason", "updated_at"])

    send_notification(
        recipient=assignment.user,
        notification_type=NotificationType.EMPLOYMENT_REJECTED,
        title="جابه‌جایی محل خدمت رد شد",
        message=f"جابه‌جایی شما به {assignment.health_house.name} رد شد. دلیل: {reason}",
        related_object=assignment,
    )

    return assignment


from django.core.exceptions import PermissionDenied

from apps.authorization.services import Authorization


@transaction.atomic
def create_employment_assignment(*, created_by, user, health_house, employment_type, start_date,
                                   is_primary=False, reason=""):
    """
    ایجاد تخصیص محل خدمت جدید توسط یک مدیر مجاز. برخلاف
    transfer_primary_employment، این تابع تخصیص قبلی را نمی‌بندد —
    برای اضافه‌کردن یک محل خدمت جدید (نه جایگزینی) استفاده می‌شود.
    """
    if not Authorization.has_permission_code(created_by, "employment.create"):
        raise PermissionDenied("این کاربر مجوز ایجاد تخصیص محل خدمت را ندارد.")

    return EmploymentAssignment.objects.create(
        user=user,
        health_house=health_house,
        employment_type=employment_type,
        start_date=start_date,
        is_primary=is_primary,
        assigned_by=created_by,
        reason=reason,
    )


@transaction.atomic
def end_employment_assignment(*, assignment, ended_by, end_date, reason=""):
    """
    پایان‌دادن به یک تخصیص فعال — رکورد هرگز حذف نمی‌شود، فقط
    is_active/end_date به‌روزرسانی می‌شود (طبق قانون Historical Data).
    """
    if not Authorization.can(ended_by, "employment.update", assignment):
        raise PermissionDenied("این کاربر مجوز پایان‌دادن به این تخصیص را ندارد.")

    assignment.is_active = False
    assignment.end_date = end_date
    if reason:
        assignment.reason = reason
    assignment.save(update_fields=["is_active", "end_date", "reason", "updated_at"])
    return assignment


