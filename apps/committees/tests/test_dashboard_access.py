from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.committees.models import Committee

User = get_user_model()


class CommitteeDashboardStaffAccessTests(TestCase):
    """طبق درخواست: staff/superuser باید بدون نیاز به RoleAssignment دسترسی داشته باشند."""

    def setUp(self):
        self.staff_user = User.objects.create_user(username="committee_staff", password="pass12345", is_staff=True)
        self.ordinary_user = User.objects.create_user(username="committee_ordinary", password="pass12345")
        self.committee = Committee.objects.create(name="کمیته تست داشبورد")

    def test_staff_can_view_committee_list(self):
        self.client.login(username="committee_staff", password="pass12345")
        response = self.client.get(reverse("committees_mgmt:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "کمیته تست داشبورد")

    def test_staff_can_view_committee_detail(self):
        self.client.login(username="committee_staff", password="pass12345")
        response = self.client.get(reverse("committees_mgmt:detail", kwargs={"pk": self.committee.pk}))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_create_committee(self):
        self.client.login(username="committee_staff", password="pass12345")
        response = self.client.post(reverse("committees_mgmt:create"), {
            "name": "کمیته جدید ایجادشده توسط استاف", "code": "", "description": "", "purpose": "", "scope": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Committee.objects.filter(name="کمیته جدید ایجادشده توسط استاف").exists())

    def test_ordinary_user_sees_empty_list(self):
        """کاربر عادی بدون Permission، فهرست خالی می‌بیند (نه خطا) — رفتار طراحی‌شده."""
        self.client.login(username="committee_ordinary", password="pass12345")
        response = self.client.get(reverse("committees_mgmt:list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "کمیته تست داشبورد")

    def test_ordinary_user_cannot_create_committee(self):
        self.client.login(username="committee_ordinary", password="pass12345")
        response = self.client.post(reverse("committees_mgmt:create"), {
            "name": "کمیته غیرمجاز", "code": "", "description": "", "purpose": "", "scope": "",
        })
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_redirected(self):
        response = self.client.get(reverse("committees_mgmt:list"))
        self.assertEqual(response.status_code, 302)