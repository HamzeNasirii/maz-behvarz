import datetime
import random

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.authorization.choices import ApprovalStatus
from apps.authorization.services import Authorization
from apps.board.permissions import is_board_leadership, is_board_member

from .choices import ALLOWED_TRANSITIONS, MembershipStatus, RemovalProposalStatus
from .models import Member, MembershipFee, MemberRemovalProposal, MembershipPeriod, MembershipStatusHistory
from . import selectors


# ------------------------------------------------------------------
# سرویس‌های فاز ۱۰ (بدون تغییر)
# ------------------------------------------------------------------

@transaction.atomic
def start_membership_period(*, member, start_date, assigned_by=None, reason=""):
    return MembershipPeriod.objects.create(
        member=member, start_date=start_date, is_active=True,
        assigned_by=assigned_by, reason=reason,
    )


@transaction.atomic
def end_membership_period(*, membership_period, end_date, reason=""):
    membership_period.end_date = end_date
    membership_period.is_active = False
    if reason:
        membership_period.reason = reason
    membership_period.save(update_fields=["end_date", "is_active", "reason", "updated_at"])
    return membership_period


@transaction.atomic
def renew_membership(*, member, new_start_date, assigned_by=None, reason=""):
    previous = MembershipPeriod.objects.for_member(member).active().select_for_update().first()
    if previous is not None:
        end_membership_period(
            membership_period=previous,
            end_date=new_start_date - datetime.timedelta(days=1),
            reason="تمدید عضویت",
        )
    return start_membership_period(
        member=member, start_date=new_start_date, assigned_by=assigned_by, reason=reason
    )


# ------------------------------------------------------------------
# سرویس‌های فاز ۱۱ — تأیید/رد درخواست اولیه‌ی عضویت (approval_status)
# این‌ها با Lifecycle فاز ۲۸ (status) کاملاً متفاوت‌اند: approval_status
# فقط نتیجه‌ی بررسی همان درخواست اولیه است.
# ------------------------------------------------------------------

@transaction.atomic
def approve_member(*, member, approved_by):
    if not Authorization.can(approved_by, "member.approve", member):
        raise PermissionDenied("این کاربر مجوز تأیید عضویت را ندارد.")
    if member.registered_by_id and member.registered_by_id == approved_by.id:
        raise PermissionDenied("ثبت‌کننده‌ی عضو نمی‌تواند تأییدکننده‌ی همان درخواست باشد.")

    member.approval_status = ApprovalStatus.APPROVED
    member.approved_by = approved_by
    member.approved_at = timezone.now()
    member.rejection_reason = ""
    member.save(update_fields=["approval_status", "approved_by", "approved_at", "rejection_reason", "updated_at"])
    return member


@transaction.atomic
def reject_member(*, member, rejected_by, reason):
    if not Authorization.can(rejected_by, "member.approve", member):
        raise PermissionDenied("این کاربر مجوز رد عضویت را ندارد.")
    if member.registered_by_id and member.registered_by_id == rejected_by.id:
        raise PermissionDenied("ثبت‌کننده‌ی عضو نمی‌تواند رد‌کننده‌ی همان درخواست باشد.")

    member.approval_status = ApprovalStatus.REJECTED
    member.approved_by = rejected_by
    member.approved_at = timezone.now()
    member.rejection_reason = reason
    member.save(update_fields=["approval_status", "approved_by", "approved_at", "rejection_reason", "updated_at"])
    return member


# ------------------------------------------------------------------
# Membership Lifecycle State Machine (فاز ۲۸)
# ------------------------------------------------------------------

def _transition(*, member, new_status, actor, reason="", comment=""):
    current_status = member.status
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"تغییر وضعیت از «{member.get_status_display()}» به این وضعیت مجاز نیست."
        )

    MembershipStatusHistory.objects.create(
        member=member, previous_status=current_status, new_status=new_status,
        actor=actor, reason=reason, comment=comment,
    )
    member.status = new_status
    member.save(update_fields=["status", "updated_at"])
    return member


@transaction.atomic
def submit_membership(*, member, actor):
    if member.user_id != actor.id:
        raise PermissionDenied("فقط خود عضو می‌تواند درخواست عضویت را ثبت کند.")
    return _transition(member=member, new_status=MembershipStatus.SUBMITTED, actor=actor)


@transaction.atomic
def review_membership(*, member, actor):
    if not Authorization.can(actor, "membership.review", member):
        raise PermissionDenied("این کاربر مجوز بررسی این درخواست عضویت را ندارد.")
    return _transition(member=member, new_status=MembershipStatus.UNDER_REVIEW, actor=actor)


@transaction.atomic
def approve_membership(*, member, actor):
    if not Authorization.can(actor, "membership.approve", member):
        raise PermissionDenied("این کاربر مجوز تأیید این عضویت را ندارد.")
    return _transition(member=member, new_status=MembershipStatus.APPROVED, actor=actor)


@transaction.atomic
def reject_membership(*, member, actor, reason):
    if not reason:
        raise ValidationError("ثبت دلیل رد درخواست الزامی است.")
    if not Authorization.can(actor, "membership.approve", member):
        raise PermissionDenied("این کاربر مجوز رد این عضویت را ندارد.")
    return _transition(member=member, new_status=MembershipStatus.REJECTED, actor=actor, reason=reason)


@transaction.atomic
def activate_membership(*, member, actor, start_date=None):
    if not Authorization.can(actor, "membership.approve", member):
        raise PermissionDenied("این کاربر مجوز فعال‌سازی این عضویت را ندارد.")
    _transition(member=member, new_status=MembershipStatus.ACTIVE, actor=actor)
    start_membership_period(
        member=member, start_date=start_date or timezone.localdate(), assigned_by=actor,
    )
    return member


@transaction.atomic
def suspend_membership(*, member, actor, reason):
    if not reason:
        raise ValidationError("ثبت دلیل تعلیق الزامی است.")
    if not Authorization.can(actor, "membership.suspend", member):
        raise PermissionDenied("این کاربر مجوز تعلیق این عضویت را ندارد.")

    current_period = MembershipPeriod.objects.for_member(member).active().first()
    if current_period is not None:
        end_membership_period(membership_period=current_period, end_date=timezone.localdate(), reason=reason)

    return _transition(member=member, new_status=MembershipStatus.SUSPENDED, actor=actor, reason=reason)


@transaction.atomic
def reinstate_membership(*, member, actor, reason=""):
    if not Authorization.can(actor, "membership.reinstate", member):
        raise PermissionDenied("این کاربر مجوز اعاده‌ی این عضویت را ندارد.")

    _transition(member=member, new_status=MembershipStatus.ACTIVE, actor=actor, reason=reason)
    start_membership_period(member=member, start_date=timezone.localdate(), assigned_by=actor, reason="اعاده‌ی عضویت")
    return member


@transaction.atomic
def expire_membership(*, member, actor, reason=""):
    if not Authorization.can(actor, "membership.expire", member):
        raise PermissionDenied("این کاربر مجوز اعلام انقضای این عضویت را ندارد.")

    current_period = MembershipPeriod.objects.for_member(member).active().first()
    if current_period is not None:
        end_membership_period(membership_period=current_period, end_date=timezone.localdate(), reason="انقضای عضویت")

    return _transition(member=member, new_status=MembershipStatus.EXPIRED, actor=actor, reason=reason)


@transaction.atomic
def cancel_membership(*, member, actor, reason):
    if not reason:
        raise ValidationError("ثبت دلیل لغو عضویت الزامی است.")
    if not Authorization.can(actor, "membership.cancel", member):
        raise PermissionDenied("این کاربر مجوز لغو این عضویت را ندارد.")

    current_period = MembershipPeriod.objects.for_member(member).active().first()
    if current_period is not None:
        end_membership_period(membership_period=current_period, end_date=timezone.localdate(), reason=reason)

    return _transition(member=member, new_status=MembershipStatus.CANCELLED, actor=actor, reason=reason)


# ------------------------------------------------------------------
# Fee (مستقل از Lifecycle — قانون Payment ≠ Membership)
# ------------------------------------------------------------------

def record_fee_payment(*, fee, paid_by, payment_date, reference_number="", payment_method="",
                       is_automated_payment=False):
    """
    ⚠️ پارامتر is_automated_payment=True فقط باید از مسیرهای پرداخت
    خودکار و امن (مثل تأیید پرداخت واقعی بله، بعد از تطبیق موفق
    payload امضاشده) صدا زده شود — هرگز مستقیم توسط کاربر یا از
    طریق فرم قابل‌تنظیم نیست.
    """
    from .choices import FeePaymentStatus

    if not is_automated_payment:
        if paid_by is None or not Authorization.can(paid_by, "membership.fee.update", fee.member):
            raise PermissionDenied("این کاربر مجوز ثبت پرداخت این حق عضویت را ندارد.")

    fee.payment_status = FeePaymentStatus.PAID
    fee.payment_date = payment_date
    fee.reference_number = reference_number
    fee.payment_method = payment_method
    fee.save(update_fields=["payment_status", "payment_date", "reference_number", "payment_method", "updated_at"])
    return fee


@transaction.atomic
def propose_member_removal(*, member, proposed_by, reason, reason_detail=""):
    if not is_board_member(proposed_by):
        raise PermissionDenied("فقط اعضای هیئت‌مدیره می‌توانند پیشنهاد حذف عضو بدهند.")
    if reason == "other" and not reason_detail.strip():
        raise ValidationError("برای دلیل «سایر»، ذکر توضیح الزامی است.")

    return MemberRemovalProposal.objects.create(
        member=member, proposed_by=proposed_by, reason=reason, reason_detail=reason_detail,
    )


@transaction.atomic
def approve_member_removal(*, proposal, actor, note=""):
    """
    ⚠️ عمداً از Authorization.can()/Full-Access Bypass عبور نمی‌کند —
    این تصمیم آگاهانه‌ی معماری است: با اینکه هر عضو هیئت‌مدیره دسترسی
    کامل دارد، تأیید نهایی حذف باید محدود به رئیس/دبیر بماند؛ ولی
    این محدودیت باید همچنان به Scope واقعی همان رئیس/دبیر پایبند
    بماند (جلوگیری از IDOR بین‌استانی).
    """
    if not (actor.is_superuser or actor.is_staff or is_board_leadership(actor)):
        raise PermissionDenied("فقط رئیس یا دبیر انجمن می‌توانند این پیشنهاد را تأیید کنند.")
    if not (actor.is_superuser or actor.is_staff):
        if not selectors._members_queryset_for(actor).filter(pk=proposal.member_id).exists():
            raise PermissionDenied("این عضو در محدوده‌ی دسترسی شما نیست.")
    if proposal.status != RemovalProposalStatus.PENDING:
        raise ValidationError("این پیشنهاد قبلاً بررسی شده است.")

    cancel_membership(
        member=proposal.member, actor=actor,
        reason=f"{proposal.get_reason_display()}: {proposal.reason_detail or note}".strip(": "),
    )

    proposal.status = RemovalProposalStatus.APPROVED
    proposal.decided_by = actor
    proposal.decided_at = timezone.now()
    proposal.decision_note = note
    proposal.save(update_fields=["status", "decided_by", "decided_at", "decision_note"])
    return proposal


@transaction.atomic
def reject_member_removal(*, proposal, actor, note=""):
    if not (actor.is_superuser or actor.is_staff or is_board_leadership(actor)):
        raise PermissionDenied("فقط رئیس یا دبیر انجمن می‌توانند این پیشنهاد را رد کنند.")
    if not (actor.is_superuser or actor.is_staff):
        if not selectors._members_queryset_for(actor).filter(pk=proposal.member_id).exists():
            raise PermissionDenied("این عضو در محدوده‌ی دسترسی شما نیست.")
    if proposal.status != RemovalProposalStatus.PENDING:
        raise ValidationError("این پیشنهاد قبلاً بررسی شده است.")

    proposal.status = RemovalProposalStatus.REJECTED
    proposal.decided_by = actor
    proposal.decided_at = timezone.now()
    proposal.decision_note = note
    proposal.save(update_fields=["status", "decided_by", "decided_at", "decision_note"])
    return proposal


def generate_unique_membership_number():
    """
    شماره‌ی عضویت تصادفی ۶ رقمی — تلاش مجدد تا زمانی که یه عدد
    تکراری‌نشده پیدا بشه (طبق درخواست صریح: عدد رندوم، نه ترتیبی).
    """
    while True:
        candidate = str(random.randint(100000, 999999))
        if not Member.objects.filter(membership_number=candidate).exists():
            return candidate


def delete_membership_fee(*, fee, actor):
    """
    حذف یک حق عضویت — فقط برای رکوردهای پرداخت‌نشده مجاز است (طبق
    اصل «هرگز رکورد مالی پرداخت‌شده حذف نشود»، حتی برای ادمین).
    """
    from .permissions import can_manage_members

    if not can_manage_members(actor):
        raise PermissionDenied("این کاربر مجوز حذف حق عضویت را ندارد.")
    if fee.payment_status != "unpaid":
        raise ValidationError("فقط حق‌عضویت‌های پرداخت‌نشده قابل حذف‌اند.")
    fee.delete()


from .choices import FeeChangeAction, FeeChangeStatus
from .models import FeeChangeRequest
from .permissions import can_manage_members as can_manage_fees


@transaction.atomic
def propose_fee_edit(*, fee, proposed_by, new_amount, new_due_date, reason):
    if not can_manage_fees(proposed_by):
        raise PermissionDenied("این کاربر مجوز درخواست اصلاح حق عضویت را ندارد.")
    return FeeChangeRequest.objects.create(
        fee=fee, member=fee.member, action=FeeChangeAction.EDIT, proposed_by=proposed_by,
        original_amount=fee.amount, original_due_date=fee.due_date,
        new_amount=new_amount, new_due_date=new_due_date, reason=reason,
    )


@transaction.atomic
def propose_fee_delete(*, fee, proposed_by, reason):
    if not can_manage_fees(proposed_by):
        raise PermissionDenied("این کاربر مجوز درخواست حذف حق عضویت را ندارد.")
    return FeeChangeRequest.objects.create(
        fee=fee, member=fee.member, action=FeeChangeAction.DELETE, proposed_by=proposed_by,
        original_amount=fee.amount, original_due_date=fee.due_date,
        reason=reason,
    )


@transaction.atomic
def approve_fee_change(*, change_request, actor, note=""):
    from apps.board.permissions import is_treasurer

    if not (actor.is_superuser or actor.is_staff or is_board_leadership(actor) or is_treasurer(actor)):
        raise PermissionDenied("فقط خزانه‌دار، رئیس، نایب‌رئیس یا دبیر می‌توانند درگیر این تصمیم باشند.")

    if change_request.status != FeeChangeStatus.PENDING:
        raise ValidationError("این درخواست قبلاً بررسی شده است.")

    # قانون ۱: پیشنهاددهنده نمی‌تواند تصمیم‌گیرنده‌ی همان درخواست باشد.
    is_admin = actor.is_superuser or actor.is_staff
    if change_request.proposed_by_id == actor.id and not is_admin:
        raise PermissionDenied("پیشنهاددهنده نمی‌تواند تأییدکننده‌ی همان درخواست باشد.")

    # قانون ۲: در مسائل مالی، حتماً باید خزانه‌دار یکی از دو طرف
    # (پیشنهاددهنده یا تصمیم‌گیرنده) باشد.
    if not is_admin:
        proposer_is_treasurer = is_treasurer(change_request.proposed_by) if change_request.proposed_by else False
        decider_is_treasurer = is_treasurer(actor)
        if not (proposer_is_treasurer or decider_is_treasurer):
            raise PermissionDenied(
                "در تصمیمات مالی، حتماً باید خزانه‌دار یکی از دو طرف (پیشنهاددهنده یا تأییدکننده) باشد.")

    fee = change_request.fee
    if fee is None:
        raise ValidationError("حق عضویت مربوط به این درخواست دیگر وجود ندارد.")
    if change_request.action == FeeChangeAction.EDIT:
        fee.amount = change_request.new_amount
        fee.due_date = change_request.new_due_date
        fee.save(update_fields=["amount", "due_date", "updated_at"])
    else:
        fee.delete()
        change_request.fee = None  # بازتاب صریح SET_NULL روی همین Instance در حافظه

    change_request.status = FeeChangeStatus.APPROVED
    change_request.decided_by = actor
    change_request.decided_at = timezone.now()
    change_request.decision_note = note
    change_request.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "fee"])
    return change_request


@transaction.atomic
def reject_fee_change(*, change_request, actor, note=""):
    from apps.board.permissions import is_treasurer

    if not (actor.is_superuser or actor.is_staff or is_board_leadership(actor) or is_treasurer(actor)):
        raise PermissionDenied("فقط خزانه‌دار، رئیس، نایب‌رئیس یا دبیر می‌توانند درگیر این تصمیم باشند.")

    if change_request.status != FeeChangeStatus.PENDING:
        raise ValidationError("این درخواست قبلاً بررسی شده است.")

    is_admin = actor.is_superuser or actor.is_staff
    if change_request.proposed_by_id == actor.id and not is_admin:
        raise PermissionDenied("پیشنهاددهنده نمی‌تواند ردکننده‌ی همان درخواست باشد.")

    if not is_admin:
        proposer_is_treasurer = is_treasurer(change_request.proposed_by) if change_request.proposed_by else False
        decider_is_treasurer = is_treasurer(actor)
        if not (proposer_is_treasurer or decider_is_treasurer):
            raise PermissionDenied(
                "در تصمیمات مالی، حتماً باید خزانه‌دار یکی از دو طرف (پیشنهاددهنده یا ردکننده) باشد.")

    change_request.status = FeeChangeStatus.REJECTED
    change_request.decided_by = actor
    change_request.decided_at = timezone.now()
    change_request.decision_note = note
    change_request.save(update_fields=["status", "decided_by", "decided_at", "decision_note"])
    return change_request

@transaction.atomic
def cancel_fee_change(*, change_request, actor):
    """فقط خود پیشنهاددهنده می‌تواند از درخواست خودش انصراف دهد — نه تأیید/رد کند."""
    if change_request.proposed_by_id != actor.id:
        raise PermissionDenied("فقط پیشنهاددهنده می‌تواند این درخواست را لغو کند.")
    if change_request.status != FeeChangeStatus.PENDING:
        raise ValidationError("این درخواست قبلاً بررسی شده است.")

    change_request.status = FeeChangeStatus.CANCELLED
    change_request.decided_at = timezone.now()
    change_request.save(update_fields=["status", "decided_at"])
    return change_request


@transaction.atomic
def verify_member_documents(*, member, actor):
    """
    تأیید کامل‌بودن مدارک عضو توسط دبیر/رئیس/نایب‌رئیس — پس از این
    تأیید، نقش «بهورز» (با محدوده‌ی همان خانه‌بهداشتِ محل خدمت اصلی)
    برای اولین بار به عضو تخصیص داده می‌شود.
    """
    from apps.board.permissions import is_board_leadership

    if not (actor.is_staff or actor.is_superuser or is_board_leadership(actor)):
        raise PermissionDenied("فقط دبیر، رئیس یا نایب‌رئیس می‌توانند مدارک را تأیید کنند.")

    if member.documents_verified_at:
        raise ValidationError("مدارک این عضو قبلاً تأیید شده است.")

    missing = []
    if not member.legal_decree_file:
        missing.append("آخرین حکم کارگزینی")
    if not member.network_letter_file:
        missing.append("نامه‌ی ممهور شبکه بهداشت")
    if not member.national_id_card_file:
        missing.append("تصویر کارت ملی")
    if not member.birth_certificate_pages.exists():
        missing.append("تصاویر شناسنامه")

    if missing:
        raise ValidationError(f"مدارک زیر هنوز کامل نیستند: {'، '.join(missing)}")

    primary_employment = member.user.employment_assignments.filter(is_primary=True, is_active=True).first()
    if primary_employment is None:
        raise ValidationError("این عضو محل خدمت فعال ثبت‌شده‌ای ندارد.")

    from apps.authorization.choices import AccessScopeType
    from apps.authorization.models import AccessScope, Role, RoleAssignment

    behvarz_role = Role.objects.get(code="BEHVARZ")
    house_scope, _ = AccessScope.objects.get_or_create(
        scope_type=AccessScopeType.HOUSE, house=primary_employment.health_house,
    )
    RoleAssignment.objects.get_or_create(
        user=member.user, role=behvarz_role, access_scope=house_scope,
        defaults={
            "start_date": timezone.localdate(), "assigned_by": actor,
            "reason": "تخصیص پس از تأیید کامل مدارک توسط دبیر/رئیس/نایب‌رئیس",
        },
    )

    member.documents_verified_at = timezone.now()
    member.documents_verified_by = actor
    member.save(update_fields=["documents_verified_at", "documents_verified_by", "updated_at"])
    return member


DOCUMENT_CHECK_MAP = {
    "legal_decree": {
        "label": "حکم کارگزینی",
        "has_file": lambda m: bool(m.legal_decree_file),
        "approved_field": "legal_decree_approved_at",
        "rejection_field": "legal_decree_rejection_reason",
        "is_multi": False,
    },
    "network_letter": {
        "label": "نامه‌ی شبکه",
        "has_file": lambda m: bool(m.network_letter_file),
        "approved_field": "network_letter_approved_at",
        "rejection_field": "network_letter_rejection_reason",
        "is_multi": False,
    },
    "national_id": {
        "label": "کارت ملی",
        "has_file": lambda m: bool(m.national_id_card_file),
        "approved_field": "national_id_approved_at",
        "rejection_field": "national_id_rejection_reason",
        "is_multi": False,
    },
    "birth_certificate": {
        "label": "شناسنامه",
        "has_file": lambda m: m.birth_certificate_pages.exists(),
        "approved_field": "birth_certificate_approved_at",
        "rejection_field": "birth_certificate_rejection_reason",
        "is_multi": True,
    },
}


def get_document_status_rows(member):
    rows = []
    for key, config in DOCUMENT_CHECK_MAP.items():
        has_file = config["has_file"](member)
        approved = bool(getattr(member, config["approved_field"]))
        rejected = bool(getattr(member, config["rejection_field"]))

        if not has_file:
            status = "missing"
        elif approved:
            status = "approved"
        elif rejected:
            status = "rejected"
        else:
            status = "pending"
        rows.append({"key": key, "label": config["label"], "status": status})
    return rows


def get_document_review_rows(member):
    rows = []
    file_field_map = {
        "legal_decree": "legal_decree_file",
        "network_letter": "network_letter_file",
        "national_id": "national_id_card_file",
    }
    for key, config in DOCUMENT_CHECK_MAP.items():
        has_file = config["has_file"](member)
        approved_at = getattr(member, config["approved_field"])
        rejection_reason = getattr(member, config["rejection_field"])

        if config["is_multi"]:
            files = [{"url": p.image.url, "name": f"صفحه‌ی {i + 1}"} for i, p in enumerate(member.birth_certificate_pages.all())]
        else:
            file_field = getattr(member, file_field_map[key])
            files = [{"url": file_field.url, "name": config["label"]}] if file_field else []

        if not has_file:
            status = "missing"
        elif approved_at:
            status = "approved"
        elif rejection_reason:
            status = "rejected"
        else:
            status = "pending"

        rows.append({
            "key": key, "label": config["label"], "status": status,
            "files": files, "rejection_reason": rejection_reason,
        })
    return rows


def _grant_behvarz_role_if_all_approved(member, actor):
    all_done = all(
        config["has_file"](member) and getattr(member, config["approved_field"])
        for config in DOCUMENT_CHECK_MAP.values()
    )
    if not all_done or member.documents_verified_at:
        return

    primary_employment = member.user.employment_assignments.filter(is_primary=True, is_active=True).first()
    if primary_employment is None:
        return

    from apps.authorization.choices import AccessScopeType
    from apps.authorization.models import AccessScope, Role, RoleAssignment

    behvarz_role = Role.objects.get(code="BEHVARZ")
    house_scope, _ = AccessScope.objects.get_or_create(
        scope_type=AccessScopeType.HOUSE, house=primary_employment.health_house,
    )
    RoleAssignment.objects.get_or_create(
        user=member.user, role=behvarz_role, access_scope=house_scope,
        defaults={
            "start_date": timezone.localdate(), "assigned_by": actor,
            "reason": "تخصیص پس از تأیید کامل مدارک توسط دبیر/رئیس/نایب‌رئیس",
        },
    )
    member.documents_verified_at = timezone.now()
    member.documents_verified_by = actor
    member.save(update_fields=["documents_verified_at", "documents_verified_by", "updated_at"])


@transaction.atomic
def approve_single_document(*, member, actor, document_key):
    from apps.board.permissions import is_board_leadership

    if not (actor.is_staff or actor.is_superuser or is_board_leadership(actor)):
        raise PermissionDenied("فقط دبیر، رئیس یا نایب‌رئیس می‌توانند مدارک را تأیید کنند.")

    config = DOCUMENT_CHECK_MAP.get(document_key)
    if config is None:
        raise ValidationError("مدرک نامعتبر است.")
    if not config["has_file"](member):
        raise ValidationError("این مدرک هنوز ارسال نشده است.")

    setattr(member, config["approved_field"], timezone.now())
    setattr(member, config["rejection_field"], "")
    member.save(update_fields=[config["approved_field"], config["rejection_field"], "updated_at"])

    _grant_behvarz_role_if_all_approved(member, actor)
    return member


@transaction.atomic
def reject_single_document(*, member, actor, document_key, reason):
    from apps.board.permissions import is_board_leadership

    if not (actor.is_staff or actor.is_superuser or is_board_leadership(actor)):
        raise PermissionDenied("فقط دبیر، رئیس یا نایب‌رئیس می‌توانند مدارک را رد کنند.")
    if not reason.strip():
        raise ValidationError("ثبت دلیل رد الزامی است.")

    config = DOCUMENT_CHECK_MAP.get(document_key)
    if config is None:
        raise ValidationError("مدرک نامعتبر است.")

    setattr(member, config["approved_field"], None)
    setattr(member, config["rejection_field"], reason)
    member.save(update_fields=[config["approved_field"], config["rejection_field"], "updated_at"])
    return member