"""
تولید/اعتبارسنجی لینک‌های امن برای «دسترسی سریع» بین صفحات مدیریتی —
به‌جای گذاشتن شناسه‌ی خام (?user=3) در URL. این یه لایه‌ی UX/Hygiene
اضافه‌ست، نه جایگزین Authorization Engine — چک واقعی مجوز همچنان در
خود Service Layer (مثل assign_role) انجام می‌شود.
"""

from django.core import signing

SALT = "behvarzan-quick-action-ref"
MAX_AGE_SECONDS = 60 * 30  # ۳۰ دقیقه — کافی برای یک جلسه‌ی کاری معمولی


def make_ref(pk):
    return signing.dumps(pk, salt=SALT)


def resolve_ref(token, max_age=MAX_AGE_SECONDS):
    """در صورت نامعتبر/منقضی‌بودن توکن، None برمی‌گرداند (نه Exception)."""
    if not token:
        return None
    try:
        return signing.loads(token, salt=SALT, max_age=max_age)
    except signing.BadSignature:
        return None