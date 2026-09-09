import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.members.models import Member, MembershipPeriod

User = get_user_model()


class MemberTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member1", password="pass12345")
        self.member = Member.objects.create(user=self.user)

    def test_member_creation(self):
        self.assertEqual(Member.objects.count(), 1)

    def test_membership_period_active(self):
        MembershipPeriod.objects.create(
            member=self.member,
            start_date=datetime.date.today() - datetime.timedelta(days=10),
        )
        self.assertTrue(
            Member.objects.with_active_membership().filter(pk=self.member.pk).exists()
        )

    def test_membership_period_expired_not_active(self):
        MembershipPeriod.objects.create(
            member=self.member,
            start_date=datetime.date.today() - datetime.timedelta(days=100),
            end_date=datetime.date.today() - datetime.timedelta(days=10),
        )
        self.assertFalse(
            Member.objects.with_active_membership().filter(pk=self.member.pk).exists()
        )


class MemberForUserScopeTests(TestCase):
    def setUp(self):
        import datetime

        from apps.authorization.choices import AccessScopeType
        from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
        from apps.employment.models import EmploymentAssignment
        from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری یک")
        sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری الف")

        babol_network = HealthNetwork.objects.create(county=babol, name="شبکه بابل")
        babol_center = HealthCenter.objects.create(network=babol_network, name="مرکز بابل یک")
        babol_house = HealthHouse.objects.create(center=babol_center, name="خانه بابل الف")

        self.viewer = User.objects.create_user(username="viewer2", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="member.view"))
        sari_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        RoleAssignment.objects.create(
            user=self.viewer, role=role, access_scope=sari_scope,
            start_date=datetime.date.today(),
        )

        sari_user = User.objects.create_user(username="sari_u2", password="pass12345")
        self.sari_member = Member.objects.create(user=sari_user)
        EmploymentAssignment.objects.create(
            user=sari_user, health_house=sari_house,
            start_date=datetime.date.today(), is_primary=True,
        )

        babol_user = User.objects.create_user(username="babol_u2", password="pass12345")
        self.babol_member = Member.objects.create(user=babol_user)
        EmploymentAssignment.objects.create(
            user=babol_user, health_house=babol_house,
            start_date=datetime.date.today(), is_primary=True,
        )

    def test_member_for_user_returns_only_in_scope_records(self):
        scoped = Member.objects.for_user(self.viewer)
        self.assertIn(self.sari_member, scoped)
        self.assertNotIn(self.babol_member, scoped)