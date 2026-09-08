from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.notifications.choices import NotificationType
from apps.notifications.services import send_notification

User = get_user_model()


class NotificationPortalIDORTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="notif_user_a", password="pass12345")
        self.user_b = User.objects.create_user(username="notif_user_b", password="pass12345")

        self.notification_a = send_notification(
            recipient=self.user_a, notification_type=NotificationType.GENERAL, title="اعلان A",
        )
        self.notification_b = send_notification(
            recipient=self.user_b, notification_type=NotificationType.GENERAL, title="اعلان B",
        )

    def test_user_can_view_own_notification(self):
        self.client.login(username="notif_user_a", password="pass12345")
        response = self.client.get(reverse("notifications_portal:detail", kwargs={"pk": self.notification_a.pk}))
        self.assertEqual(response.status_code, 200)

    def test_idor_cannot_view_other_user_notification(self):
        self.client.login(username="notif_user_a", password="pass12345")
        response = self.client.get(reverse("notifications_portal:detail", kwargs={"pk": self.notification_b.pk}))
        self.assertEqual(response.status_code, 403)

    def test_list_only_shows_own_notifications(self):
        self.client.login(username="notif_user_a", password="pass12345")
        response = self.client.get(reverse("notifications_portal:list"))
        self.assertContains(response, "اعلان A")
        self.assertNotContains(response, "اعلان B")

    def test_mark_read_only_for_own_notification(self):
        self.client.login(username="notif_user_a", password="pass12345")
        response = self.client.post(reverse("notifications_portal:mark_read", kwargs={"pk": self.notification_b.pk}))
        self.assertEqual(response.status_code, 403)

    def test_mark_own_read_works(self):
        self.client.login(username="notif_user_a", password="pass12345")
        self.client.post(reverse("notifications_portal:mark_read", kwargs={"pk": self.notification_a.pk}))
        self.notification_a.refresh_from_db()
        self.assertTrue(self.notification_a.is_read)

    def test_mark_all_read(self):
        self.client.login(username="notif_user_a", password="pass12345")
        self.client.post(reverse("notifications_portal:mark_all_read"))
        self.notification_a.refresh_from_db()
        self.assertTrue(self.notification_a.is_read)
        self.notification_b.refresh_from_db()
        self.assertFalse(self.notification_b.is_read)  # مال کاربر دیگه، نباید تغییر کنه