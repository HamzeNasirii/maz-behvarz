from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.authorization.services import Authorization
from apps.notifications.choices import NotificationType
from apps.notifications.services import send_notification

from .choices import ALLOWED_REQUEST_TRANSITIONS, RequestStatus, RequestType
from .models import Request, RequestHistory
from .target_validation import validate_target_object



@transaction.atomic
def create_request(*, requester, request_type, title, description="", scope=None, content_object=None):
    validate_target_object(content_object)
    return Request.objects.create(
        requester=requester, request_type=request_type, title=title,
        description=description, scope=scope, content_object=content_object,
    )


def _transition(*, request_obj, new_status, actor, reason=""):
    allowed = ALLOWED_REQUEST_TRANSITIONS.get(request_obj.status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"تغییر وضعیت از «{request_obj.get_status_display()}» به این وضعیت مجاز نیست."
        )

    RequestHistory.objects.create(
        request=request_obj, from_status=request_obj.status, to_status=new_status,
        changed_by=actor, reason=reason,
    )

    request_obj.status = new_status
    if new_status == RequestStatus.SUBMITTED:
        request_obj.submitted_at = timezone.now()
    if new_status == RequestStatus.APPROVED:
        request_obj.approved_by = actor
        request_obj.approved_at = timezone.now()
    if new_status == RequestStatus.COMPLETED:
        request_obj.completed_at = timezone.now()
    if new_status == RequestStatus.CANCELLED:
        request_obj.cancelled_at = timezone.now()

    request_obj.save()
    return request_obj


def _notify_requester(request_obj, notification_type, title):
    """
    فقط به requester اطلاع می‌دهیم (قطعی و بدون ابهام). طبق بخش ۳۰
    سند، Audience سمت Reviewer به‌عمد Wire نشده (Business Rule نامشخص).
    """
    send_notification(
        recipient=request_obj.requester, notification_type=notification_type,
        title=title, related_object=request_obj,
    )


@transaction.atomic
def submit_request(*, request_obj, actor, reason=""):
    if request_obj.requester_id != actor.id:
        raise PermissionDenied("فقط ثبت‌کننده‌ی درخواست می‌تواند آن را ارسال کند.")
    request_obj = _transition(request_obj=request_obj, new_status=RequestStatus.SUBMITTED, actor=actor, reason=reason)
    return request_obj


@transaction.atomic
def start_request_review(*, request_obj, actor, reason=""):
    if not Authorization.can(actor, "request.review", request_obj):
        raise PermissionDenied("این کاربر مجوز بررسی این درخواست را ندارد.")
    request_obj = Request.objects.select_for_update().get(pk=request_obj.pk)
    return _transition(request_obj=request_obj, new_status=RequestStatus.UNDER_REVIEW, actor=actor, reason=reason)


def _apply_domain_action_on_approve(request_obj, actor, reason=""):
    """
    یکپارچگی با Domain واقعی — طبق بخش ۴۰ سند فقط برای EMPLOYMENT_TRANSFER
    (تنها موردی که Business Rule صریح و بدون ابهام داشت). برای انواع
    دیگر عمداً هیچ اقدامی انجام نمی‌شود (BUSINESS RULE DECISION REQUIRED،
    مستند در REQUEST_WORKFLOW_ARCHITECTURE.md).
    """
    if request_obj.request_type == RequestType.EMPLOYMENT_TRANSFER:
        from apps.employment.models import EmploymentAssignment
        from apps.employment.services import approve_employment_transfer

        if isinstance(request_obj.content_object, EmploymentAssignment):
            approve_employment_transfer(assignment=request_obj.content_object, approved_by=actor)


def _apply_domain_action_on_reject(request_obj, actor, reason):
    if request_obj.request_type == RequestType.EMPLOYMENT_TRANSFER:
        from apps.employment.models import EmploymentAssignment
        from apps.employment.services import reject_employment_transfer

        if isinstance(request_obj.content_object, EmploymentAssignment):
            reject_employment_transfer(assignment=request_obj.content_object, rejected_by=actor, reason=reason)


@transaction.atomic
def approve_request(*, request_obj, actor, reason=""):
    if not Authorization.can(actor, "request.approve", request_obj):
        raise PermissionDenied("این کاربر مجوز تأیید این درخواست را ندارد.")
    if request_obj.requester_id == actor.id and not actor.is_superuser:
        raise PermissionDenied("ثبت‌کننده‌ی درخواست نمی‌تواند تأییدکننده‌ی همان درخواست باشد.")

    request_obj = Request.objects.select_for_update().get(pk=request_obj.pk)
    _apply_domain_action_on_approve(request_obj, actor, reason)
    request_obj = _transition(request_obj=request_obj, new_status=RequestStatus.APPROVED, actor=actor, reason=reason)
    _notify_requester(request_obj, NotificationType.GENERAL, "درخواست شما تأیید شد")
    return request_obj


@transaction.atomic
def reject_request(*, request_obj, actor, reason):
    if not reason:
        raise ValidationError("ثبت دلیل رد درخواست الزامی است.")
    if not Authorization.can(actor, "request.reject", request_obj):
        raise PermissionDenied("این کاربر مجوز رد این درخواست را ندارد.")
    if request_obj.requester_id == actor.id and not actor.is_superuser:
        raise PermissionDenied("ثبت‌کننده‌ی درخواست نمی‌تواند ردکننده‌ی همان درخواست باشد.")

    request_obj = Request.objects.select_for_update().get(pk=request_obj.pk)
    _apply_domain_action_on_reject(request_obj, actor, reason)
    request_obj = _transition(request_obj=request_obj, new_status=RequestStatus.REJECTED, actor=actor, reason=reason)
    _notify_requester(request_obj, NotificationType.GENERAL, "درخواست شما رد شد")
    return request_obj


@transaction.atomic
def return_request(*, request_obj, actor, reason):
    if not reason:
        raise ValidationError("ثبت دلیل بازگشت درخواست الزامی است.")
    if not Authorization.can(actor, "request.return", request_obj):
        raise PermissionDenied("این کاربر مجوز بازگرداندن این درخواست را ندارد.")

    request_obj = Request.objects.select_for_update().get(pk=request_obj.pk)
    request_obj = _transition(request_obj=request_obj, new_status=RequestStatus.RETURNED, actor=actor, reason=reason)
    _notify_requester(request_obj, NotificationType.GENERAL, "درخواست شما نیاز به اصلاح دارد")
    return request_obj


@transaction.atomic
def resubmit_request(*, request_obj, actor, reason=""):
    if request_obj.requester_id != actor.id:
        raise PermissionDenied("فقط ثبت‌کننده‌ی درخواست می‌تواند آن را دوباره ارسال کند.")
    request_obj = Request.objects.select_for_update().get(pk=request_obj.pk)
    return _transition(request_obj=request_obj, new_status=RequestStatus.RESUBMITTED, actor=actor, reason=reason)


@transaction.atomic
def cancel_request(*, request_obj, actor, reason=""):
    is_owner = request_obj.requester_id == actor.id
    if not is_owner and not Authorization.can(actor, "request.cancel", request_obj):
        raise PermissionDenied("این کاربر مجوز لغو این درخواست را ندارد.")

    request_obj = Request.objects.select_for_update().get(pk=request_obj.pk)
    return _transition(request_obj=request_obj, new_status=RequestStatus.CANCELLED, actor=actor, reason=reason)


@transaction.atomic
def complete_request(*, request_obj, actor, reason=""):
    if not Authorization.can(actor, "request.complete", request_obj):
        raise PermissionDenied("این کاربر مجوز تکمیل این درخواست را ندارد.")

    request_obj = Request.objects.select_for_update().get(pk=request_obj.pk)
    request_obj = _transition(request_obj=request_obj, new_status=RequestStatus.COMPLETED, actor=actor, reason=reason)
    _notify_requester(request_obj, NotificationType.GENERAL, "درخواست شما تکمیل شد")
    return request_obj