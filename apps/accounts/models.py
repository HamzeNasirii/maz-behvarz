from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

from .managers import CustomUserManager


class CustomUser(AbstractUser):
    """
    Custom User Foundation (Phase 01).

    عمداً شامل موارد زیر نیست:
    - فیلد مستقیم Role
    - ForeignKey مستقیم به HealthHouse

    Role و Employment در فازهای بعدی توسط مدل‌های مستقل
    RoleAssignment / EmploymentAssignment مدیریت می‌شوند، تا یک
    کاربر بتواند هم‌زمان چند Role داشته باشد و در طول زمان در چند
    HealthHouse فعالیت کند.
    """

    email = models.EmailField(blank=True)
    profile_picture = models.ImageField(
        upload_to="profile_pictures/%Y/%m/", blank=True, null=True, verbose_name="تصویر پروفایل",
    )
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="تاریخ تولد")
    nickname = models.CharField(
        max_length=50, blank=True, unique=True, null=True, verbose_name="نام نمایشی",
        help_text="این نام به‌جای نام کاربری برای دیگران نمایش داده می‌شود؛ کلید ورود نیست.",
    )
    must_change_password = models.BooleanField(
        default=False, verbose_name="الزام تغییر رمز عبور",
        help_text="در اولین ورود، کاربر مجبور به تغییر رمز عبور خود می‌شود.",
    )
    bale_chat_id = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name="شناسه چت بله")
    bale_link_code = models.CharField(max_length=10, blank=True, null=True)
    bale_link_code_expires_at = models.DateTimeField(blank=True, null=True)
    objects = CustomUserManager()

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return self.nickname or self.get_full_name() or self.username

    def display_name(self):
        """نام قابل‌نمایش به دیگران — هرگز شماره ملی/نام کاربری را افشا نمی‌کند مگر Nickname تنظیم نشده باشد."""
        return self.nickname or self.get_full_name() or "کاربر بدون نام"


class PasswordResetCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reset_codes")
    code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)


