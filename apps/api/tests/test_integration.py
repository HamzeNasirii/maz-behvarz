import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.authorization.choices import ApprovalStatus
from apps.employment.models import EmploymentAssignment
from apps.members.models import Member
from apps.notifications.models import Notification
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province
from apps.website.models import MembershipApplication
from apps.website.services import approve_membership_application
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


class FullMembershipJourneyTests(TestCase):
    """
    سناریوی کامل: درخواست عمومی → تأیید ادمین → ورود به پنل →
    مشاهده‌ی اطلاعیه → دسترسی API با توکن.
    """

    def setUp(self):
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=center, name="خانه الف")
        self.admin = User.objects.create_superuser(
            username="journey_admin", password="pass12345", email="a@a.com"
        )

    def test_full_journey(self):
        # ۱. ثبت درخواست عضویت از فرم عمومی
        response = self.client.post(
            reverse("website:membership_application"),
            {
                "first_name": "علی",
                "last_name": "رضایی",
                "national_code": "1231231230",
                "mobile_number": "09121234567",
                "province": self.house.center.network.county.province_id,
                "county": self.house.center.network.county_id,
                "network": self.house.center.network_id,
                "center": self.house.center_id,
                "health_house": self.house.id,
                "accepted_terms": "on",
                "legal_decree_file": SimpleUploadedFile("decree.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
                "network_letter_file": SimpleUploadedFile("letter.pdf", b"%PDF-1.4 fake",
                                                          content_type="application/pdf"),
            },
        )
        self.assertEqual(response.status_code, 302)
        application = MembershipApplication.objects.get(national_code="1231231230")
        self.assertEqual(application.status, ApprovalStatus.PENDING)

        # ۲. تأیید توسط ادمین (از طریق Service، معادل Admin Action)
        user = approve_membership_application(application=application, approved_by=self.admin)
        self.assertTrue(Member.objects.filter(user=user).exists())
        self.assertTrue(EmploymentAssignment.objects.filter(user=user, is_primary=True).exists())

        # ۳. اطلاعیه ساخته شده باشد
        self.assertTrue(Notification.objects.for_user(user).filter(
            notification_type="membership_approved"
        ).exists())

        # ۴. کاربر تازه‌ساخته‌شده باید بتونه (بعد از تنظیم رمز فرضی) وارد پنل بشه
        user.set_password("newpass12345")
        user.must_change_password = False
        user.save()
        self.client.login(username=user.username, password="newpass12345")
        response = self.client.get(reverse("members_portal:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.house.name)

        # ۵. دسترسی API با توکن
        token = Token.objects.create(user=user)
        api_client = APIClient()
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.get("/api/v1/members/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)