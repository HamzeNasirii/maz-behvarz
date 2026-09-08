from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.website.models import MembershipApplication
from apps.website.services import approve_membership_application
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

User = get_user_model()


class DefaultPasswordTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران رمز تست")
        county = County.objects.create(province=province, name="ساری رمز تست")
        network = HealthNetwork.objects.create(county=county, name="شبکه رمز تست")
        center = HealthCenter.objects.create(network=network, name="مرکز رمز تست")
        self.house = HealthHouse.objects.create(center=center, name="خانه رمز تست")

        self.approver = User.objects.create_superuser(
            username="pwd_approver", password="pass12345", email="a@a.com"
        )
        self.application = MembershipApplication.objects.create(
            full_name="متقاضی رمز تست", national_code="1231234321", mobile_number="09120000005",
            health_house=self.house, accepted_terms=True,
        )

    def test_default_password_is_national_code(self):
        user = approve_membership_application(application=self.application, approved_by=self.approver)
        self.assertTrue(user.check_password("1231234321"))

    def test_user_can_login_with_default_password(self):
        approve_membership_application(application=self.application, approved_by=self.approver)
        logged_in = self.client.login(username="1231234321", password="1231234321")
        self.assertTrue(logged_in)


class ReferenceManagementAccessTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username="ref_staff", password="pass12345", is_staff=True)
        self.ordinary_user = User.objects.create_user(username="ref_ordinary", password="pass12345")

    def test_staff_can_access_role_list(self):
        self.client.login(username="ref_staff", password="pass12345")
        response = self.client.get(reverse("auth_ref:role_list"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_access_permission_list(self):
        self.client.login(username="ref_staff", password="pass12345")
        response = self.client.get(reverse("auth_ref:permission_list"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_access_scope_list(self):
        self.client.login(username="ref_staff", password="pass12345")
        response = self.client.get(reverse("auth_ref:scope_list"))
        self.assertEqual(response.status_code, 200)

    def test_ordinary_user_denied(self):
        self.client.login(username="ref_ordinary", password="pass12345")
        response = self.client.get(reverse("auth_ref:role_list"))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_redirected(self):
        response = self.client.get(reverse("auth_ref:role_list"))
        self.assertEqual(response.status_code, 302)


class AccessScopeFormCascadingTests(TestCase):
    def setUp(self):
        from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

        self.province = Province.objects.create(name="مازندران آبشاری تست")
        self.county = County.objects.create(province=self.province, name="ساری آبشاری تست")
        self.network = HealthNetwork.objects.create(county=self.county, name="شبکه ساری آبشاری تست")
        self.center = HealthCenter.objects.create(network=self.network, name="مرکز آبشاری تست")
        self.house = HealthHouse.objects.create(center=self.center, name="خانه آبشاری تست")

        self.staff_user = User.objects.create_user(username="cascade_staff", password="pass12345", is_staff=True)

    def test_county_api_scoped_to_province(self):
        self.client.login(username="cascade_staff", password="pass12345")
        response = self.client.get(f"/api/organization/counties/?province={self.province.id}")
        data = response.json()
        names = [item["name"] for item in data["results"]]
        self.assertIn("ساری آبشاری تست", names)

    def test_create_access_scope_with_full_chain(self):
        self.client.login(username="cascade_staff", password="pass12345")
        response = self.client.post(reverse("auth_ref:scope_create"), {
            "scope_type": "house",
            "province": self.province.id, "county": self.county.id,
            "network": self.network.id, "center": self.center.id, "house": self.house.id,
        })
        self.assertEqual(response.status_code, 302)
        from apps.authorization.models import AccessScope
        self.assertTrue(AccessScope.objects.filter(house=self.house).exists())
