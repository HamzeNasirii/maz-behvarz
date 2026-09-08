import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.employment.models import EmploymentAssignment
from apps.organization.models import Province, County, HealthNetwork, HealthCenter, HealthHouse

User = get_user_model()


class EmploymentAssignmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="behvarz1", password="pass12345")
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house_a = HealthHouse.objects.create(center=center, name="خانه الف")
        self.house_b = HealthHouse.objects.create(center=center, name="خانه ب")

    def test_user_can_have_two_simultaneous_employments(self):
        EmploymentAssignment.objects.create(
            user=self.user, health_house=self.house_a,
            start_date=datetime.date.today(), is_primary=True,
        )
        EmploymentAssignment.objects.create(
            user=self.user, health_house=self.house_b,
            start_date=datetime.date.today(), is_primary=False,
        )
        self.assertEqual(
            EmploymentAssignment.objects.for_user(self.user).active().count(), 2
        )

    def test_only_one_active_primary_assignment_allowed(self):
        EmploymentAssignment.objects.create(
            user=self.user, health_house=self.house_a,
            start_date=datetime.date.today(), is_primary=True,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EmploymentAssignment.objects.create(
                    user=self.user, health_house=self.house_b,
                    start_date=datetime.date.today(), is_primary=True,
                )