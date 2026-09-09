import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.employment.models import EmploymentAssignment
from apps.members.models import Member
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

User = get_user_model()


class IDORProtectionTests(TestCase):
    """
    طبق طراحی فعلی، هیچ View پورتال از ID در URL برای ارجاع به رکورد
    استفاده نمی‌کند (همیشه request.user) — این تست همین طراحی را
    تثبیت می‌کند تا در آینده کسی سهواً View با <int:pk> اضافه نکند.
    """

    def setUp(self):
        self.user_a = User.objects.create_user(username="idor_a", password="pass12345")
        self.user_b = User.objects.create_user(username="idor_b", password="pass12345")
        self.member_a = Member.objects.create(user=self.user_a)
        self.member_b = Member.objects.create(user=self.user_b)

        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        house = HealthHouse.objects.create(center=center, name="خانه الف")

        EmploymentAssignment.objects.create(
            user=self.user_b, health_house=house, start_date=datetime.date.today(), is_primary=True,
        )

    def test_profile_url_has_no_id_parameter(self):
        """تضمین می‌کند مسیر پروفایل شکل /profile/<id>/ ندارد."""
        url = reverse("members_portal:profile")
        self.assertNotIn(str(self.member_a.pk), url)
        self.assertEqual(url, "/portal/profile/")

    def test_user_a_dashboard_never_shows_user_b_employment(self):
        self.client.login(username="idor_a", password="pass12345")
        response = self.client.get(reverse("members_portal:dashboard"))
        self.assertNotContains(response, "خانه الف")

    def test_user_a_employment_history_never_shows_user_b_data(self):
        self.client.login(username="idor_a", password="pass12345")
        response = self.client.get(reverse("members_portal:employment_history"))
        self.assertNotContains(response, "خانه الف")


class RoleEscalationTests(TestCase):
    """
    User معمولی نباید بتواند با POST/Form Manipulation نقش یا Scope
    خودش را تغییر دهد — چون فرم Profile Edit اصلاً فیلدی برای
    Role/Scope ندارد، این حمله در سطح فرم مسدود است.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="escalation_user", password="pass12345")
        self.behvarz = Role.objects.get(code="BEHVARZ")
        self.county_rep = Role.objects.get(code="COUNTY_REPRESENTATIVE")

        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        self.assignment = RoleAssignment.objects.create(
            user=self.user, role=self.behvarz, access_scope=scope, start_date=datetime.date.today(),
        )

    def test_profile_edit_form_cannot_change_role(self):
        self.client.login(username="escalation_user", password="pass12345")
        response = self.client.post(reverse("members_portal:profile_edit"), {
            "first_name": "تست",
            "last_name": "کاربر",
            "email": "test@example.com",
            "role": self.county_rep.pk,  # تلاش برای تزریق فیلد غیرمجاز
        })
        self.assertEqual(response.status_code, 302)

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.role, self.behvarz)  # نقش تغییر نکرده است


class EmploymentManipulationTests(TestCase):
    """
    User نباید بتواند HealthHouse خودش را از فرم Profile تغییر دهد —
    چون فرم اصلاً چنین فیلدی ندارد.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="employment_manip_user", password="pass12345")
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house_a = HealthHouse.objects.create(center=center, name="خانه الف")
        self.house_b = HealthHouse.objects.create(center=center, name="خانه ب")
        self.assignment = EmploymentAssignment.objects.create(
            user=self.user, health_house=self.house_a, start_date=datetime.date.today(), is_primary=True,
        )

    def test_profile_edit_form_cannot_change_health_house(self):
        self.client.login(username="employment_manip_user", password="pass12345")
        response = self.client.post(reverse("members_portal:profile_edit"), {
            "first_name": "تست",
            "last_name": "کاربر",
            "email": "test@example.com",
            "health_house": self.house_b.pk,  # تلاش برای تزریق فیلد غیرمجاز
        })
        self.assertEqual(response.status_code, 302)

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.health_house, self.house_a)


class InactiveUserTests(TestCase):
    def test_inactive_user_cannot_login(self):
        user = User.objects.create_user(username="inactive_user", password="pass12345")
        user.is_active = False
        user.save()

        logged_in = self.client.login(username="inactive_user", password="pass12345")
        self.assertFalse(logged_in)

    def test_inactive_user_cannot_access_portal_even_with_existing_session(self):
        user = User.objects.create_user(username="inactive_user2", password="pass12345")
        self.client.login(username="inactive_user2", password="pass12345")
        user.is_active = False
        user.save()

        response = self.client.get(reverse("members_portal:dashboard"))
        # Django به‌صورت پیش‌فرض سشن غیرفعال را برای کاربر غیرفعال باطل می‌کند
        self.assertNotEqual(response.status_code, 200)


class ProfileEditFieldRestrictionTests(TestCase):
    def test_only_identity_fields_are_editable(self):
        from apps.members.forms import ProfileEditForm

        allowed_fields = set(ProfileEditForm.Meta.fields)
        forbidden_fields = {"role", "health_house", "access_scope", "approval_status", "is_staff", "is_superuser"}
        self.assertEqual(allowed_fields & forbidden_fields, set())