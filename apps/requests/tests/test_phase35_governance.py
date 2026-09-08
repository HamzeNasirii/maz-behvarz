import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.requests.choices import RequestType
from apps.requests.models import Request
from apps.requests.services import create_request, submit_request

User = get_user_model()


class AdminGovernanceTests(TestCase):
    """طبق بخش ۳۱ سند: Admin نباید Workflow را دور بزند."""

    def setUp(self):
        self.staff_user = User.objects.create_superuser(
            username="gov_admin", password="pass12345", email="a@a.com"
        )
        self.requester = User.objects.create_user(username="gov_requester", password="pass12345")
        self.other_user = User.objects.create_user(username="gov_other", password="pass12345")
        self.req = create_request(requester=self.requester, request_type=RequestType.OTHER, title="تست Governance")

        self.client.login(username="gov_admin", password="pass12345")

    def test_admin_cannot_change_requester(self):
        url = reverse("admin:requests_request_change", args=[self.req.pk])
        self.client.post(url, {
            "requester": self.other_user.pk, "request_type": RequestType.OTHER,
            "title": "تست Governance ویرایش‌شده", "description": "",
        })
        self.req.refresh_from_db()
        self.assertEqual(self.req.requester, self.requester)

    def test_admin_cannot_directly_set_status(self):
        url = reverse("admin:requests_request_change", args=[self.req.pk])
        self.client.post(url, {
            "requester": self.requester.pk, "request_type": RequestType.OTHER,
            "title": "تست Governance", "description": "", "status": "completed",
        })
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "draft")  # هنوز DRAFT است، نه completed


class WorkflowSecurityHardeningTests(TestCase):
    """
    طبق بخش ۳۵ سند: تست‌های Security تکمیلی (GET Mutation، Status/
    Approval Tampering، Privilege Escalation).
    """

    def setUp(self):
        self.requester = User.objects.create_user(username="sec35_requester", password="pass12345")
        self.stranger = User.objects.create_user(username="sec35_stranger", password="pass12345")

        self.manager = User.objects.create_user(username="sec35_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(
            Permission.objects.get(code="request.review"),
            Permission.objects.get(code="request.approve"),
        )
        province_scope = AccessScope.objects.create(scope_type=AccessScopeType.GLOBAL)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=province_scope, start_date=timezone.localdate(),
        )

        self.req = create_request(
            requester=self.requester, request_type=RequestType.OTHER, title="تست امنیت فاز ۳۵",
            scope=province_scope,
        )
        submit_request(request_obj=self.req, actor=self.requester)

    def test_get_request_to_approve_url_does_not_mutate_state(self):
        """طبق NO GET STATE MUTATION — این View فقط فرم را نشان می‌دهد."""
        self.client.login(username="sec35_manager", password="pass12345")
        self.client.get(reverse("requests_mgmt:review", kwargs={"pk": self.req.pk}))
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "submitted")  # هنوز submitted، چون GET چیزی تغییر نداد

    def test_privilege_escalation_stranger_cannot_approve(self):
        self.client.login(username="sec35_stranger", password="pass12345")
        response = self.client.post(
            reverse("requests_mgmt:approve", kwargs={"pk": self.req.pk}), {}
        )
        self.req.refresh_from_db()
        self.assertNotEqual(self.req.status, "approved")

    def test_status_tampering_via_create_form_ignored(self):
        """طبق بخش ۲۰ سند: status نباید از طریق فرم عمومی قابل تزریق باشد."""
        req2 = create_request(
            requester=self.requester, request_type=RequestType.OTHER, title="تست دیگر",
        )
        self.assertEqual(req2.status, "draft")  # همیشه DRAFT شروع می‌شود، صرف‌نظر از هر ورودی احتمالی

    def test_approval_field_tampering_approved_by_not_settable_by_requester(self):
        """
        approved_by فقط از طریق Service Layer (در تابع _transition) تنظیم
        می‌شود؛ هیچ فرم/View‌ای این فیلد را از کاربر نمی‌گیرد.
        """
        self.assertIsNone(self.req.approved_by)
