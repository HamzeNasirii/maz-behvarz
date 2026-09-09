import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.employment.models import EmploymentAssignment
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

from ..models import Member

User = get_user_model()


class MemberPortalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="portal_user", password="pass12345")
        self.member = Member.objects.create(user=self.user)

        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=center, name="خانه الف")

        EmploymentAssignment.objects.create(
            user=self.user, health_house=self.house,
            start_date=datetime.date.today(), is_primary=True,
        )

    def test_portal_requires_login(self):
        response = self.client.get(reverse("members_portal:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_portal_shows_own_data(self):
        self.client.login(username="portal_user", password="pass12345")
        response = self.client.get(reverse("members_portal:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.house.name)

    def test_employment_history_view(self):
        self.client.login(username="portal_user", password="pass12345")
        response = self.client.get(reverse("members_portal:employment_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.house.name)

class ProfilePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile_user", password="pass12345", first_name="حمزه", last_name="نصیری"
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse("members_portal:profile"))
        self.assertEqual(response.status_code, 302)

    def test_profile_shows_own_data(self):
        self.client.login(username="profile_user", password="pass12345")
        response = self.client.get(reverse("members_portal:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "حمزه")