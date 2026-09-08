import random
from datetime import timedelta

from django.utils import timezone

from .bale_client import send_message
from .models import PasswordResetCode


def generate_link_code(user):
    code = str(random.randint(100000, 999999))
    user.bale_link_code = code
    user.bale_link_code_expires_at = timezone.now() + timedelta(minutes=10)
    user.save(update_fields=["bale_link_code", "bale_link_code_expires_at"])
    return code


def try_link_from_update(update):
    """پردازش یک Update دریافتی از getUpdates — تلاش برای تطبیق متن پیام با یک کد اتصال معتبر."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    message = update.get("message")
    if not message or "text" not in message:
        return

    text = message["text"].strip()
    chat_id = str(message["chat"]["id"])

    user = User.objects.filter(
        bale_link_code=text, bale_link_code_expires_at__gt=timezone.now()
    ).first()
    if user:
        user.bale_chat_id = chat_id
        user.bale_link_code = None
        user.bale_link_code_expires_at = None
        user.save(update_fields=["bale_chat_id", "bale_link_code", "bale_link_code_expires_at"])
        send_message(chat_id, "✅ حساب بله شما با موفقیت به سامانه انجمن صنفی بهورزان متصل شد.")


def send_password_reset_code(user):
    if not user.bale_chat_id:
        raise ValueError("این کاربر حساب بله متصل‌شده ندارد.")

    code = str(random.randint(100000, 999999))
    PasswordResetCode.objects.create(
        user=user, code=code, expires_at=timezone.now() + timedelta(minutes=10),
    )
    send_message(
        user.bale_chat_id,
        f"کد بازیابی رمز عبور شما: *{code}*\nاین کد تا ۱۰ دقیقه معتبر است.",
    )


def verify_reset_code(user, code):
    reset_code = PasswordResetCode.objects.filter(
        user=user, code=code, is_used=False, expires_at__gt=timezone.now()
    ).order_by("-created_at").first()
    if reset_code is None:
        return False
    reset_code.is_used = True
    reset_code.save(update_fields=["is_used"])
    return True