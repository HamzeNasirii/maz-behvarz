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


class MemberManagementIDORTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری یک")
        sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری الف")

        babol_network = HealthNetwork.objects.create(county=babol, name="شبکه بابل")
        babol_center = HealthCenter.objects.create(network=babol_network, name="مرکز بابل یک")
        babol_house = HealthHouse.objects.create(center=babol_center, name="خانه بابل الف")

        sari_user = User.objects.create_user(username="sari_member_v", password="pass12345")
        self.sari_member = Member.objects.create(user=sari_user)
        EmploymentAssignment.objects.create(
            user=sari_user, health_house=sari_house, start_date=datetime.date.today(), is_primary=True,
        )

        babol_user = User.objects.create_user(username="babol_member_v", password="pass12345")
        self.babol_member = Member.objects.create(user=babol_user)
        EmploymentAssignment.objects.create(
            user=babol_user, health_house=babol_house, start_date=datetime.date.today(), is_primary=True,
        )

        self.manager = User.objects.create_user(username="sari_member_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="member.view"))
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

    def test_manager_can_view_in_scope_member(self):
        self.client.login(username="sari_member_manager", password="pass12345")
        response = self.client.get(reverse("members_portal:member_detail", kwargs={"pk": self.sari_member.pk}))
        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_view_out_of_scope_member(self):
        self.client.login(username="sari_member_manager", password="pass12345")
        response = self.client.get(reverse("members_portal:member_detail", kwargs={"pk": self.babol_member.pk}))
        self.assertEqual(response.status_code, 403)

    def test_member_list_only_shows_in_scope_members(self):
        self.client.login(username="sari_member_manager", password="pass12345")
        response = self.client.get(reverse("members_portal:member_list"))
        self.assertContains(response, "sari_member_v")
        self.assertNotContains(response, "babol_member_v")


class MemberSearchTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username="1234567890", password="pass12345", is_staff=True)
        target_user = User.objects.create_user(
            username="9876543210", password="pass12345", first_name="حمزه", last_name="نصیری",
        )
        Member.objects.create(user=target_user)

    def test_search_by_first_name(self):
        self.client.login(username="1234567890", password="pass12345")
        response = self.client.get(reverse("members_portal:member_list"), {"q": "حمزه"})
        self.assertContains(response, "حمزه")

    def test_search_by_national_code(self):
        self.client.login(username="1234567890", password="pass12345")
        response = self.client.get(reverse("members_portal:member_list"), {"q": "9876543210"})
        self.assertContains(response, "9876543210")

    def test_suggestions_endpoint_returns_json(self):
        self.client.login(username="1234567890", password="pass12345")
        response = self.client.get(reverse("members_portal:member_search_suggestions"), {"q": "حم"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["national_code"], "9876543210")

    def test_suggestions_require_min_two_chars(self):
        self.client.login(username="1234567890", password="pass12345")
        response = self.client.get(reverse("members_portal:member_search_suggestions"), {"q": "ح"})
        self.assertEqual(response.json()["results"], [])


class QuickRoleAssignmentPrefillTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username="qra_staff", password="pass12345", is_staff=True)
        self.target_user = User.objects.create_user(username="qra_target", password="pass12345")

    def test_role_list_filtered_by_user_param(self):
        import datetime

        from django.utils import timezone

        from apps.authorization.choices import AccessScopeType
        from apps.authorization.models import AccessScope, Role, RoleAssignment
        from apps.authorization.secure_links import make_ref

        role = Role.objects.get(code="BEHVARZ")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.GLOBAL)
        RoleAssignment.objects.create(
            user=self.target_user, role=role, access_scope=scope, start_date=timezone.localdate(),
        )
        other_user = User.objects.create_user(username="qra_other", password="pass12345")
        RoleAssignment.objects.create(
            user=other_user, role=role, access_scope=scope, start_date=timezone.localdate(),
        )

        self.client.login(username="qra_staff", password="pass12345")
        ref = make_ref(self.target_user.pk)
        response = self.client.get(reverse("roles:management_list") + f"?ref={ref}")
        self.assertContains(response, "qra_target")
        self.assertNotContains(response, "qra_other")


class SecureRefTests(TestCase):
    def test_ref_roundtrip(self):
        from apps.authorization.secure_links import make_ref, resolve_ref

        token = make_ref(42)
        self.assertEqual(resolve_ref(token), 42)

    def test_tampered_ref_rejected(self):
        from apps.authorization.secure_links import make_ref, resolve_ref

        token = make_ref(42)
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        self.assertIsNone(resolve_ref(tampered))

    def test_ref_not_a_sequential_integer(self):
        from apps.authorization.secure_links import make_ref

        token = make_ref(3)
        self.assertNotEqual(token, "3")
        self.assertGreater(len(token), 5)


class MembershipNumberGenerationTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران عضویت تست")
        county = County.objects.create(province=province, name="ساری عضویت تست")
        network = HealthNetwork.objects.create(county=county, name="شبکه عضویت تست")
        center = HealthCenter.objects.create(network=network, name="مرکز عضویت تست")
        self.house = HealthHouse.objects.create(center=center, name="خانه عضویت تست")
        self.approver = User.objects.create_superuser(
            username="membnum_approver", password="pass12345", email="a@a.com"
        )

    def test_membership_number_is_generated_and_unique(self):
        from apps.website.models import MembershipApplication
        from apps.website.services import approve_membership_application

        app1 = MembershipApplication.objects.create(
            full_name="متقاضی یک", national_code="1112223341", mobile_number="09121112221",
            health_house=self.house, accepted_terms=True,
        )
        app2 = MembershipApplication.objects.create(
            full_name="متقاضی دو", national_code="1112223342", mobile_number="09121112222",
            health_house=self.house, accepted_terms=True,
        )
        user1 = approve_membership_application(application=app1, approved_by=self.approver)
        user2 = approve_membership_application(application=app2, approved_by=self.approver)

        member1 = Member.objects.get(user=user1)
        member2 = Member.objects.get(user=user2)

        self.assertTrue(member1.membership_number.isdigit())
        self.assertEqual(len(member1.membership_number), 6)
        self.assertNotEqual(member1.membership_number, member2.membership_number)

    def test_mobile_number_copied_from_application(self):
        from apps.website.models import MembershipApplication
        from apps.website.services import approve_membership_application

        app = MembershipApplication.objects.create(
            full_name="متقاضی موبایل", national_code="1112223343", mobile_number="09123334444",
            health_house=self.house, accepted_terms=True,
        )
        user = approve_membership_application(application=app, approved_by=self.approver)
        member = Member.objects.get(user=user)
        self.assertEqual(member.mobile_number, "09123334444")