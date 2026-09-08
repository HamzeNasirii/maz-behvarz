from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.members.choices import MembershipStatus
from apps.authorization.choices import ApprovalStatus
from apps.employment.models import EmploymentAssignment
from apps.members.models import Member, MembershipPeriod
from apps.notifications.choices import NotificationType
from apps.notifications.services import send_notification
User = get_user_model()


@transaction.atomic
def approve_membership_application(*, application, approved_by, start_date=None):
    """
    تبدیل یک درخواست عضویت تأییدشده به User + Member + MembershipPeriod
    + EmploymentAssignment واقعی. کاربر تازه‌ساخته‌شده با رمز غیرقابل‌استفاده
    ساخته می‌شود (فاز Notifications باید مکانیزم تنظیم رمز اولیه را اضافه کند).
    """
    if application.status != ApprovalStatus.PENDING:
        raise PermissionDenied("این درخواست قبلاً بررسی شده است.")

    start_date = start_date or timezone.localdate()

    name_parts = application.full_name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    user = User.objects.create_user(
        username=application.national_code,
        password=application.national_code,
        first_name=first_name,
        last_name=last_name,
        must_change_password=True,
    )

    from apps.members.services import generate_unique_membership_number

    member = Member.objects.create(
        user=user,
        registered_by=approved_by,
        approval_status=ApprovalStatus.APPROVED,
        approved_by=approved_by,
        approved_at=timezone.now(),
        status=MembershipStatus.ACTIVE,
        membership_number=generate_unique_membership_number(),
        mobile_number=application.mobile_number,
    )

    MembershipPeriod.objects.create(
        member=member, start_date=start_date, assigned_by=approved_by,
    )

    EmploymentAssignment.objects.create(
        user=user,
        health_house=application.health_house,
        start_date=start_date,
        is_primary=True,
        assigned_by=approved_by,
        approval_status=ApprovalStatus.APPROVED,
        approved_by=approved_by,
        approved_at=timezone.now(),
    )

    application.status = ApprovalStatus.APPROVED
    application.reviewed_by = approved_by
    application.save(update_fields=["status", "reviewed_by", "updated_at"])

    province_name = (
        application.health_house.center.network.county.province.name
        if application.health_house else "مازندران"
    )

    send_notification(
        recipient=user,
        notification_type=NotificationType.MEMBERSHIP_APPROVED,
        title=f"🎉 به انجمن صنفی بهورزان استان {province_name} خوش آمدید!",
        message=(
            f"{first_name} عزیز، عضویت شما در انجمن صنفی بهورزان استان {province_name} با موفقیت تأیید شد. "
            "خوشحالیم که شما را در جمع خانواده‌ی بزرگ بهورزان استان می‌بینیم. "
            "برایتان در این مسیر آرزوی سلامتی و موفقیت روزافزون داریم."
        ),
        related_object=member,
    )

    return user


@transaction.atomic
def reject_membership_application(*, application, rejected_by, note=""):
    if application.status != ApprovalStatus.PENDING:
        raise PermissionDenied("این درخواست قبلاً بررسی شده است.")

    application.status = ApprovalStatus.REJECTED
    application.reviewed_by = rejected_by
    application.review_note = note
    application.save(update_fields=["status", "reviewed_by", "review_note", "updated_at"])

    # توجه: چون کاربر واقعی هنوز ساخته نشده (درخواست رد شده)، اطلاع‌رسانی
    # این مرحله در فاز SMS/Email (که با موبایل درخواست‌دهنده کار می‌کند نه
    # حساب کاربری) پیاده خواهد شد. اینجا فقط رکورد رد در خود Application ثبت می‌شود.

    return application