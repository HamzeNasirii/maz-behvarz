import datetime

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.employment.models import EmploymentAssignment
from apps.members.models import Member
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province
from apps.notifications.services import send_notification
from apps.notifications.choices import NotificationType

User = get_user_model()


class MemberApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="api_user", password="pass12345")
        self.member = Member.objects.create(user=self.user)
        self.token = Token.objects.create(user=self.user)

        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=center, name="خانه الف")
        EmploymentAssignment.objects.create(
            user=self.user, health_house=self.house, start_date=datetime.date.today(), is_primary=True,
        )

    def test_unauthenticated_request_denied(self):
        response = self.client.get("/api/v1/members/")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_sees_own_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.get("/api/v1/members/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_authenticated_user_sees_own_employment(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.get("/api/v1/employment-assignments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_notification_mark_read_endpoint(self):
        notification = send_notification(
            recipient=self.user, notification_type=NotificationType.GENERAL, title="تست API",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post(f"/api/v1/notifications/{notification.id}/mark_read/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_read"])

    def test_membership_application_creation_is_public(self):
        response = self.client.post(
            "/api/v1/membership-applications/",
            {
                "full_name": "تست ای‌پی‌آی",
                "national_code": "5556667778",
                "mobile_number": "09121112233",
                "health_house": self.house.id,
                "accepted_terms": True,
            },
        )
        self.assertEqual(response.status_code, 201)