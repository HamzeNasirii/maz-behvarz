from django.contrib.auth.models import UserManager


class CustomUserManager(UserManager):
    """
    زیرکلاس نازک UserManager پیش‌فرض جنگو.

    عمداً به‌عنوان Extension Point نگه داشته شده: در فازهای بعدی
    (مثلاً تغییر روش ورود به شماره موبایل) می‌توان create_user /
    create_superuser را همین‌جا بازنویسی کرد بدون تغییر جای دیگری
    از پروژه که از این Manager استفاده می‌کند.
    """

    pass