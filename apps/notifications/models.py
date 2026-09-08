from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .choices import NotificationType
from .managers import NotificationQuerySet

class Notification(models.Model):
    """
    Infrastructure پایه‌ی اطلاع‌رسانی درون‌برنامه‌ای. ارسال SMS/Email
    واقعی خارج از دامنه‌ی این مرحله است؛ این مدل نقطه‌ی اتصال آن‌ها
    در فازهای بعدی خواهد بود.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=30, choices=NotificationType.choices, default=NotificationType.GENERAL, db_index=True
    )
    title = models.CharField(max_length=150)
    message = models.CharField(max_length=500, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    objects = NotificationQuerySet.as_manager()
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "اطلاعیه"
        verbose_name_plural = "اطلاعیه‌ها"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"{self.title} → {self.recipient}"