import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employment.models import EmploymentAssignment
from apps.employment.services import transfer_primary_employment
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province
from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

User = get_user_model()


class TransferPrimaryEmploymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="behvarz1", password="pass12345")
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house_a = HealthHouse.objects.create(center=center, name="خانه الف")
        self.house_b = HealthHouse.objects.create(center=center, name="خانه ب")

        self.first = EmploymentAssignment.objects.create(
            user=self.user, health_house=self.house_a,
            start_date=datetime.date(2024, 1, 1), is_primary=True,
        )

    def test_transfer_closes_previous_and_creates_new(self):
        new_assignment = transfer_primary_employment(
            user=self.user,
            new_health_house=self.house_b,
            effective_date=datetime.date(2025, 1, 1),
        )

        self.first.refresh_from_db()
        self.assertFalse(self.first.is_active)
        self.assertEqual(self.first.end_date, datetime.date(2025, 1, 1))

        self.assertTrue(new_assignment.is_active)
        self.assertTrue(new_assignment.is_primary)
        self.assertEqual(new_assignment.health_house, self.house_b)

        # هیچ رکوردی حذف نشده — فقط بسته و اضافه شده
        self.assertEqual(EmploymentAssignment.objects.for_user(self.user).count(), 2)

    def test_only_one_active_primary_after_transfer(self):
        transfer_primary_employment(
            user=self.user,
            new_health_house=self.house_b,
            effective_date=datetime.date(2025, 1, 1),
        )
        active_primary_count = (
            EmploymentAssignment.objects.for_user(self.user)
            .active()
            .filter(is_primary=True)
            .count()
        )
        self.assertEqual(active_primary_count, 1)



from apps.authorization.choices import ApprovalStatus
from apps.employment.services import approve_employment_transfer
from apps.notifications.models import Notification


class EmploymentApprovalNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="emp_notif_user", password="pass12345")
        self.approver = User.objects.create_user(username="emp_notif_approver", password="pass12345")

        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        house = HealthHouse.objects.create(center=center, name="خانه الف")

        self.assignment = EmploymentAssignment.objects.create(
            user=self.user, health_house=house, start_date=datetime.date.today(),
        )

        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="employment.approve"))
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.approver, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

    def test_notification_sent_on_approval(self):
        approve_employment_transfer(assignment=self.assignment, approved_by=self.approver)
        self.assertTrue(
            Notification.objects.for_user(self.user).filter(
                notification_type="employment_approved"
            ).exists()
        )