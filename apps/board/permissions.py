from .choices import BoardPosition
from .models import BoardMembership


def is_board_member(user):
    """هر یک از سمت‌های هیئت‌مدیره — برای دسترسی کامل عمومی (سطح استان)."""
    if not user.is_authenticated:
        return False
    return BoardMembership.objects.filter(user=user, is_active=True).exists()


def is_role_decision_authority(user):
    """
    فقط رئیس، نایب‌رئیس و دبیر — تنها این سه سمت (به‌علاوه‌ی Staff/
    Superuser که در جای دیگر چک می‌شود) مجاز به تصمیم نهایی
    (تأیید/رد) روی تخصیص نقش‌ها هستند. طبق تصمیم صریح، این محدودتر
    از is_board_member است.
    """
    if not user.is_authenticated:
        return False
    return BoardMembership.objects.filter(
        user=user, is_active=True,
        position__in=[BoardPosition.CHAIRMAN, BoardPosition.VICE_CHAIRMAN, BoardPosition.SECRETARY],
    ).exists()


def is_board_leadership(user):
    """
    نگه‌داشته‌شده برای سازگاری عقب‌رو با کدهای قبلی (مثلاً پنل مدیریت
    سازمانی/گزارش‌ها) — معادل is_role_decision_authority است.
    """
    return is_role_decision_authority(user)

def is_treasurer(user):
    """آیا کاربر عضو فعال هیئت‌مدیره با سمت خزانه‌دار است؟"""
    if not user.is_authenticated:
        return False
    return BoardMembership.objects.filter(
        user=user, is_active=True, position=BoardPosition.TREASURER,
    ).exists()


def get_active_board_position_label(user):
    """برچسب دقیق سمت فعلی کاربر در هیئت‌مدیره (اگر عضو باشد)، وگرنه رشته‌ی خالی."""
    if not user or not user.is_authenticated:
        return ""
    membership = BoardMembership.objects.filter(user=user, is_active=True).first()
    return membership.get_position_display() if membership else ""


