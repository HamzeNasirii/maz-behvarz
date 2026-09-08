from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.authorization.services import Authorization

from .choices import ALLOWED_BOARD_TRANSITIONS, BoardStatus
from .models import Board, BoardMembership, BoardStatusHistory


def _transition(*, board, new_status, actor, reason=""):
    allowed = ALLOWED_BOARD_TRANSITIONS.get(board.status, set())
    if new_status not in allowed:
        raise ValidationError(f"تغییر وضعیت از «{board.get_status_display()}» به این وضعیت مجاز نیست.")

    BoardStatusHistory.objects.create(
        board=board, previous_status=board.status, new_status=new_status, actor=actor, reason=reason,
    )
    board.status = new_status
    board.save(update_fields=["status", "updated_at"])
    return board


@transaction.atomic
def create_board(*, created_by, start_date, end_date=None, description=""):
    if not Authorization.has_permission_code(created_by, "board.create"):
        raise PermissionDenied("این کاربر مجوز ایجاد دوره‌ی هیئت‌مدیره را ندارد.")

    next_number = Board.objects.count() + 1
    name = f"دوره {next_number}"
    return Board.objects.create(name=name, start_date=start_date, end_date=end_date, description=description)

@transaction.atomic
def activate_board(*, board, actor, reason=""):
    if not Authorization.has_permission_code(actor, "board.update"):
        raise PermissionDenied("این کاربر مجوز فعال‌سازی این دوره را ندارد.")
    return _transition(board=board, new_status=BoardStatus.ACTIVE, actor=actor, reason=reason)


@transaction.atomic
def suspend_board(*, board, actor, reason):
    if not reason:
        raise ValidationError("ثبت دلیل تعلیق الزامی است.")
    if not Authorization.has_permission_code(actor, "board.update"):
        raise PermissionDenied("این کاربر مجوز تعلیق این دوره را ندارد.")
    return _transition(board=board, new_status=BoardStatus.SUSPENDED, actor=actor, reason=reason)


@transaction.atomic
def end_board(*, board, actor, reason=""):
    if not Authorization.has_permission_code(actor, "board.update"):
        raise PermissionDenied("این کاربر مجوز پایان‌دادن به این دوره را ندارد.")
    return _transition(board=board, new_status=BoardStatus.ENDED, actor=actor, reason=reason)


@transaction.atomic
def archive_board(*, board, actor, reason=""):
    if not Authorization.has_permission_code(actor, "board.delete"):
        raise PermissionDenied("این کاربر مجوز بایگانی این دوره را ندارد.")
    return _transition(board=board, new_status=BoardStatus.ARCHIVED, actor=actor, reason=reason)


@transaction.atomic
def add_board_member(*, board, user, position, added_by, start_date, reason=""):
    if not Authorization.has_permission_code(added_by, "board.manage_members"):
        raise PermissionDenied("این کاربر مجوز افزودن عضو هیئت‌مدیره را ندارد.")
    if added_by.id == user.id and not added_by.is_superuser:
        raise PermissionDenied("کاربر نمی‌تواند خودش را عضو هیئت‌مدیره کند.")

    return BoardMembership.objects.create(
        board=board, user=user, position=position, start_date=start_date,
        assigned_by=added_by, reason=reason,
    )


@transaction.atomic
def remove_board_member(*, membership, removed_by, end_date, reason=""):
    if not Authorization.has_permission_code(removed_by, "board.manage_members"):
        raise PermissionDenied("این کاربر مجوز حذف این عضو را ندارد.")

    membership.is_active = False
    membership.end_date = end_date
    if reason:
        membership.reason = reason
    membership.save(update_fields=["is_active", "end_date", "reason", "updated_at"])
    return membership


# --- تابع قدیمی فاز ۱۴ (بدون تغییر، برای سازگاری عقب‌رو حفظ شد) ---
@transaction.atomic
def end_board_membership(*, membership, end_date, reason=""):
    membership.end_date = end_date
    membership.is_active = False
    if reason:
        membership.reason = reason
    membership.save(update_fields=["end_date", "is_active", "reason", "updated_at"])
    return membership