
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.authorization.services import Authorization

from .authorization import can_manage_committee
from .choices import ALLOWED_COMMITTEE_TRANSITIONS, CommitteeStatus
from .models import Committee, CommitteeMembership, CommitteeStatusHistory

@transaction.atomic
def end_committee_membership(*, membership, end_date, reason=""):
    membership.end_date = end_date
    membership.is_active = False
    if reason:
        membership.reason = reason
    membership.save(update_fields=["end_date", "is_active", "reason", "updated_at"])
    return membership




def _transition(*, committee, new_status, actor, reason=""):
    allowed = ALLOWED_COMMITTEE_TRANSITIONS.get(committee.status, set())
    if new_status not in allowed:
        raise ValidationError(f"تغییر وضعیت از «{committee.get_status_display()}» به این وضعیت مجاز نیست.")

    CommitteeStatusHistory.objects.create(
        committee=committee, previous_status=committee.status, new_status=new_status,
        actor=actor, reason=reason,
    )
    committee.status = new_status
    committee.is_active = new_status == CommitteeStatus.ACTIVE
    committee.save(update_fields=["status", "is_active", "updated_at"])
    return committee


@transaction.atomic
def create_committee(*, created_by, name, description="", purpose="", scope=None, code=None):
    if not (created_by.is_superuser or created_by.is_staff
            or Authorization.has_permission_code(created_by, "committee.create")):
        raise PermissionDenied("این کاربر مجوز ایجاد کمیته را ندارد.")
    return Committee.objects.create(
        name=name, description=description, purpose=purpose, scope=scope, code=code,
    )

@transaction.atomic
def activate_committee(*, committee, actor, reason=""):
    if not can_manage_committee(actor, committee, "committee.update"):
        raise PermissionDenied("این کاربر مجوز فعال‌سازی این کمیته را ندارد.")
    return _transition(committee=committee, new_status=CommitteeStatus.ACTIVE, actor=actor, reason=reason)


@transaction.atomic
def suspend_committee(*, committee, actor, reason):
    if not reason:
        raise ValidationError("ثبت دلیل تعلیق الزامی است.")
    if not can_manage_committee(actor, committee, "committee.update"):
        raise PermissionDenied("این کاربر مجوز تعلیق این کمیته را ندارد.")
    return _transition(committee=committee, new_status=CommitteeStatus.SUSPENDED, actor=actor, reason=reason)


@transaction.atomic
def end_committee(*, committee, actor, reason=""):
    if not can_manage_committee(actor, committee, "committee.update"):
        raise PermissionDenied("این کاربر مجوز پایان‌دادن به این کمیته را ندارد.")
    return _transition(committee=committee, new_status=CommitteeStatus.ENDED, actor=actor, reason=reason)


@transaction.atomic
def archive_committee(*, committee, actor, reason=""):
    if not can_manage_committee(actor, committee, "committee.delete"):
        raise PermissionDenied("این کاربر مجوز بایگانی این کمیته را ندارد.")
    return _transition(committee=committee, new_status=CommitteeStatus.ARCHIVED, actor=actor, reason=reason)


@transaction.atomic
def add_committee_member(*, committee, user, added_by, start_date, reason=""):
    if not can_manage_committee(added_by, committee, "committee.manage_members"):
        raise PermissionDenied("این کاربر مجوز افزودن عضو به این کمیته را ندارد.")
    if added_by.id == user.id and not added_by.is_superuser:
        raise PermissionDenied("کاربر نمی‌تواند خودش را به کمیته اضافه کند.")

    return CommitteeMembership.objects.create(
        committee=committee, user=user, start_date=start_date, assigned_by=added_by, reason=reason,
    )


@transaction.atomic
def remove_committee_member(*, membership, removed_by, end_date, reason=""):
    if not can_manage_committee(removed_by, membership.committee, "committee.manage_members"):
        raise PermissionDenied("این کاربر مجوز حذف عضو از این کمیته را ندارد.")

    membership.is_active = False
    membership.end_date = end_date
    if reason:
        membership.reason = reason
    membership.save(update_fields=["is_active", "end_date", "reason", "updated_at"])
    return membership