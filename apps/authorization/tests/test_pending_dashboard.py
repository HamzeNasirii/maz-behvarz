from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.board.choices import BoardPosition
from apps.board.models import BoardMembership

User = get_user_model()


class PendingDashboardAccessTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username="pd_staff", password="pass12345", is_staff=True)
        self.chairman = User.objects.create_user(username="pd_chairman", password="pass12345")
        BoardMembership.objects.create(
            user=self.chairman, position=BoardPosition.CHAIRMAN, start_date=timezone.localdate(),
        )
        self.secretary = User.objects.create_user(username="pd_secretary", password="pass12345")
        BoardMembership.objects.create(
            user=self.secretary, position=BoardPosition.SECRETARY, start_date=timezone.localdate(),
        )
        self.ordinary_user = User.objects.create_user(username="pd_ordinary", password="pass12345")
        self.plain_board_member = User.objects.create_user(username="pd_plain_board", password="pass12345")
        BoardMembership.objects.create(
            user=self.plain_board_member, position=BoardPosition.MEMBER, start_date=timezone.localdate(),
        )

    def test_staff_can_access(self):
        self.client.login(username="pd_staff", password="pass12345")
        response = self.client.get(reverse("pending_requests"))
        self.assertEqual(response.status_code, 200)

    def test_chairman_can_access(self):
        self.client.login(username="pd_chairman", password="pass12345")
        response = self.client.get(reverse("pending_requests"))
        self.assertEqual(response.status_code, 200)

    def test_secretary_can_access(self):
        self.client.login(username="pd_secretary", password="pass12345")
        response = self.client.get(reverse("pending_requests"))
        self.assertEqual(response.status_code, 200)

    def test_ordinary_user_denied(self):
        self.client.login(username="pd_ordinary", password="pass12345")
        response = self.client.get(reverse("pending_requests"))
        self.assertEqual(response.status_code, 403)

    def test_plain_board_member_denied(self):
        """طبق Rule صریح: فقط رئیس و دبیر، نه هر عضو هیئت‌مدیره."""
        self.client.login(username="pd_plain_board", password="pass12345")
        response = self.client.get(reverse("pending_requests"))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_redirected(self):
        response = self.client.get(reverse("pending_requests"))
        self.assertEqual(response.status_code, 302)