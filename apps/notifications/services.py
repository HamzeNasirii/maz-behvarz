from django.db import transaction
from django.utils import timezone

from .models import Notification


@transaction.atomic
def send_notification(*, recipient, notification_type, title, message="", related_object=None):
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        content_object=related_object,
    )


@transaction.atomic
def mark_as_read(*, notification):
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save(update_fields=["is_read", "read_at"])
    return notification

@transaction.atomic
def notify_users_in_scope(*, access_scope, notification_type, title, message="", related_object=None):
    """
    Extension Point آماده طبق بخش ۳۶/۴۸ سند — عمداً در هیچ‌جای دیگری
    خودکار صدا زده نمی‌شود، چون هیچ Business Rule صریحی برای «کدام
    مخاطب باید اعلان بگیرد» تعریف نشده است.
    """
    from apps.authorization.models import RoleAssignment

    target_house_ids = set(access_scope.get_health_house_queryset().values_list("pk", flat=True))
    notified_user_ids = set()

    for assignment in RoleAssignment.objects.active().select_related("access_scope"):
        if assignment.user_id in notified_user_ids:
            continue
        assignment_houses = set(assignment.access_scope.get_health_house_queryset().values_list("pk", flat=True))
        if target_house_ids and not (assignment_houses & target_house_ids):
            continue
        notified_user_ids.add(assignment.user_id)
        send_notification(
            recipient=assignment.user, notification_type=notification_type,
            title=title, message=message, related_object=related_object,
        )