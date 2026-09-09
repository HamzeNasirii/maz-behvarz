from django.core.exceptions import PermissionDenied
from django.db import transaction

from .choices import ContentStatus
from .models import ContactMessage


@transaction.atomic
def submit_contact_message(*, name, email, phone, subject, message):
    """
    طبق STEP 23 سند: پیام مستقیم به ایمیل ارسال نمی‌شود، فقط در
    دیتابیس ذخیره می‌شود تا ادمین از طریق Admin بررسی کند.
    """
    return ContactMessage.objects.create(
        name=name, email=email, phone=phone, subject=subject, message=message
    )


@transaction.atomic
def publish_content(*, instance, published_by=None):
    """
    برای مدل‌هایی با فیلد status (NewsArticle, Event, Regulation).
    """
    from django.utils import timezone

    if not hasattr(instance, "status"):
        raise ValueError("این آبجکت فیلد status ندارد.")

    instance.status = ContentStatus.PUBLISHED
    if not instance.published_at:
        instance.published_at = timezone.now()
    instance.save(update_fields=["status", "published_at", "updated_at"])
    return instance


@transaction.atomic
def archive_content(*, instance):
    if not hasattr(instance, "status"):
        raise ValueError("این آبجکت فیلد status ندارد.")

    instance.status = ContentStatus.ARCHIVED
    instance.save(update_fields=["status", "updated_at"])
    return instance