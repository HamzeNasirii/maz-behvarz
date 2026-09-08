import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.board.choices import BoardPosition
from apps.board.models import BoardMembership
from apps.organization.models import County, Province

User = get_user_model()


class OrganizationManagementAccessTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username="org_staff", password="pass12345", is_staff=True)
        self.chairman = User.objects.create_user(username="org_chairman", password="pass12345")
        BoardMembership.objects.create(
            user=self.chairman, position=BoardPosition.CHAIRMAN, start_date=timezone.localdate(),
        )
        self.secretary = User.objects.create_user(username="org_secretary", password="pass12345")
        BoardMembership.objects.create(
            user=self.secretary, position=BoardPosition.SECRETARY, start_date=timezone.localdate(),
        )
        self.ordinary_user = User.objects.create_user(username="org_ordinary", password="pass12345")

        self.province = Province.objects.create(name="مازندران تست مدیریت")

    def test_staff_can_access_tree(self):
        self.client.login(username="org_staff", password="pass12345")
        response = self.client.get(reverse("org_mgmt:tree"))
        self.assertEqual(response.status_code, 200)

    def test_chairman_can_access_tree(self):
        self.client.login(username="org_chairman", password="pass12345")
        response = self.client.get(reverse("org_mgmt:tree"))
        self.assertEqual(response.status_code, 200)

    def test_secretary_can_access_tree(self):
        self.client.login(username="org_secretary", password="pass12345")
        response = self.client.get(reverse("org_mgmt:tree"))
        self.assertEqual(response.status_code, 200)

    def test_ordinary_user_cannot_access_tree(self):
        self.client.login(username="org_ordinary", password="pass12345")
        response = self.client.get(reverse("org_mgmt:tree"))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_redirected_to_login(self):
        response = self.client.get(reverse("org_mgmt:tree"))
        self.assertEqual(response.status_code, 302)

    def test_inactive_board_member_denied(self):
        """عضویت هیئت‌مدیره‌ی پایان‌یافته نباید دسترسی بدهد."""
        ex_chairman = User.objects.create_user(username="org_ex_chairman", password="pass12345")
        BoardMembership.objects.create(
            user=ex_chairman, position=BoardPosition.CHAIRMAN,
            start_date=datetime.date(2020, 1, 1), end_date=datetime.date(2021, 1, 1), is_active=False,
        )
        self.client.login(username="org_ex_chairman", password="pass12345")
        response = self.client.get(reverse("org_mgmt:tree"))
        self.assertEqual(response.status_code, 403)

    def test_regular_board_member_without_position_denied(self):
        """طبق Rule صریح: فقط رئیس و دبیر، نه هر عضو هیئت‌مدیره."""
        plain_member = User.objects.create_user(username="org_plain_board", password="pass12345")
        BoardMembership.objects.create(
            user=plain_member, position=BoardPosition.MEMBER, start_date=timezone.localdate(),
        )
        self.client.login(username="org_plain_board", password="pass12345")
        response = self.client.get(reverse("org_mgmt:tree"))
        self.assertEqual(response.status_code, 403)


class OrganizationManagementCRUDTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username="org_crud_staff", password="pass12345", is_staff=True)
        self.province = Province.objects.create(name="استان تست CRUD")
        self.client.login(username="org_crud_staff", password="pass12345")

    def test_create_county(self):
        response = self.client.post(
            reverse("org_mgmt:create", kwargs={"level": "county"}) + f"?parent={self.province.id}",
            {"name": "شهرستان جدید تست", "code": "", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        county = County.objects.get(name="شهرستان جدید تست")
        self.assertEqual(county.province, self.province)

    def test_edit_county_cannot_change_parent(self):
        county = County.objects.create(province=self.province, name="شهرستان ثابت تست")
        other_province = Province.objects.create(name="استان دیگر تست")

        response = self.client.post(reverse("org_mgmt:edit", kwargs={"level": "county", "pk": county.pk}), {
            "name": "شهرستان ثابت تست ویرایش‌شده", "code": "", "is_active": "on",
            "province": other_province.id,  # تلاش برای تزریق فیلد غیرمجاز
        })
        self.assertEqual(response.status_code, 302)
        county.refresh_from_db()
        self.assertEqual(county.province, self.province)  # والد تغییر نکرده
        self.assertEqual(county.name, "شهرستان ثابت تست ویرایش‌شده")

    def test_toggle_deactivates_without_deleting(self):
        county = County.objects.create(province=self.province, name="شهرستان برای غیرفعال‌سازی")
        response = self.client.post(reverse("org_mgmt:toggle", kwargs={"level": "county", "pk": county.pk}))
        self.assertEqual(response.status_code, 302)
        county.refresh_from_db()
        self.assertFalse(county.is_active)
        self.assertTrue(County.objects.filter(pk=county.pk).exists())  # حذف نشده، فقط غیرفعال

    def test_invalid_level_returns_403(self):
        response = self.client.get(reverse("org_mgmt:create", kwargs={"level": "invalid_level"}))
        self.assertEqual(response.status_code, 403)
