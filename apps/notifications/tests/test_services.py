from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.notifications.choices import NotificationType
from apps.notifications.models import Notification
from apps.notifications.services import mark_as_read, send_notification

User = get_user_model()


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="notif_user", password="pass12345")

    def test_send_notification_creates_record(self):
        notification = send_notification(
            recipient=self.user, notification_type=NotificationType.GENERAL, title="تست",
        )
        self.assertFalse(notification.is_read)
        self.assertEqual(Notification.objects.for_user(self.user).count(), 1)

    def test_mark_as_read(self):
        notification = send_notification(
            recipient=self.user, notification_type=NotificationType.GENERAL, title="تست",
        )
        mark_as_read(notification=notification)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertEqual(Notification.objects.for_user(self.user).unread().count(), 0)


