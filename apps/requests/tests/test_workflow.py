import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.employment.models import EmploymentAssignment
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province
from apps.requests.choices import RequestStatus, RequestType
from apps.requests.models import Request
from apps.requests.services import (
    approve_request,
    cancel_request,
    complete_request,
    create_request,
    reject_request,
    resubmit_request,
    return_request,
    start_request_review,
    submit_request,
)

User = get_user_model()


class RequestLifecycleTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(username="req_user1", password="pass12345")
        self.manager = User.objects.create_user(username="req_manager1", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(
            Permission.objects.get(code="request.view"),
            Permission.objects.get(code="request.review"),
            Permission.objects.get(code="request.approve"),
            Permission.objects.get(code="request.reject"),
            Permission.objects.get(code="request.return"),
            Permission.objects.get(code="request.complete"),
        )
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=timezone.localdate(),
        )
        self.scope = scope

    def test_create_request_starts_as_draft(self):
        req = create_request(requester=self.requester, request_type=RequestType.OTHER, title="تست")
        self.assertEqual(req.status, RequestStatus.DRAFT)

    def test_only_requester_can_submit(self):
        req = create_request(requester=self.requester, request_type=RequestType.OTHER, title="تست")
        with self.assertRaises(PermissionDenied):
            submit_request(request_obj=req, actor=self.manager)

    def test_full_happy_path(self):
        req = create_request(requester=self.requester, request_type=RequestType.OTHER, title="تست", scope=self.scope)
        submit_request(request_obj=req, actor=self.requester)
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.SUBMITTED)

        start_request_review(request_obj=req, actor=self.manager)
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.UNDER_REVIEW)

        approve_request(request_obj=req, actor=self.manager)
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.APPROVED)
        self.assertEqual(req.approved_by, self.manager)

        complete_request(request_obj=req, actor=self.manager)
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.COMPLETED)
        self.assertIsNotNone(req.completed_at)

    def test_rejection_requires_reason(self):
        req = create_request(requester=self.requester, request_type=RequestType.OTHER, title="تست", scope=self.scope)
        submit_request(request_obj=req, actor=self.requester)
        start_request_review(request_obj=req, actor=self.manager)
        with self.assertRaises(ValidationError):
            reject_request(request_obj=req, actor=self.manager, reason="")

    def test_return_and_resubmit_path(self):
        req = create_request(requester=self.requester, request_type=RequestType.OTHER, title="تست", scope=self.scope)
        submit_request(request_obj=req, actor=self.requester)
        start_request_review(request_obj=req, actor=self.manager)
        return_request(request_obj=req, actor=self.manager, reason="نیاز به مدارک بیشتر")
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.RETURNED)

        resubmit_request(request_obj=req, actor=self.requester)
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.RESUBMITTED)

    def test_self_approval_blocked(self):
        req = create_request(requester=self.manager, request_type=RequestType.OTHER, title="تست", scope=self.scope)
        submit_request(request_obj=req, actor=self.manager)
        start_request_review(request_obj=req, actor=self.manager)
        with self.assertRaises(PermissionDenied):
            approve_request(request_obj=req, actor=self.manager)

    def test_invalid_transition_completed_cannot_reapprove(self):
        req = create_request(requester=self.requester, request_type=RequestType.OTHER, title="تست", scope=self.scope)
        req.status = RequestStatus.COMPLETED
        req.save()
        with self.assertRaises(ValidationError):
            approve_request(request_obj=req, actor=self.manager)

    def test_cancel_by_owner(self):
        req = create_request(requester=self.requester, request_type=RequestType.OTHER, title="تست")
        cancel_request(request_obj=req, actor=self.requester)
        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.CANCELLED)

    def test_history_recorded(self):
        req = create_request(requester=self.requester, request_type=RequestType.OTHER, title="تست", scope=self.scope)
        submit_request(request_obj=req, actor=self.requester)
        history = req.history.first()
        self.assertEqual(history.from_status, RequestStatus.DRAFT)
        self.assertEqual(history.to_status, RequestStatus.SUBMITTED)
        self.assertEqual(history.changed_by, self.requester)


class EmploymentTransferRequestIntegrationTests(TestCase):
    """طبق بخش ۴۰ سند: تنها Integration دامنه‌ای که Business Rule صریح داشت."""

    def setUp(self):
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=center, name="خانه الف")

        self.behvarz = User.objects.create_user(username="req_behvarz", password="pass12345")
        self.assignment = EmploymentAssignment.objects.create(
            user=self.behvarz, health_house=self.house, start_date=timezone.localdate(),
        )

        self.manager = User.objects.create_user(username="req_emp_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(
            Permission.objects.get(code="request.review"),
            Permission.objects.get(code="request.approve"),
            Permission.objects.get(code="employment.approve"),
        )
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=timezone.localdate(),
        )

        self.req = create_request(
            requester=self.behvarz, request_type=RequestType.EMPLOYMENT_TRANSFER,
            title="درخواست تغییر محل خدمت", scope=scope, content_object=self.assignment,
        )
        submit_request(request_obj=self.req, actor=self.behvarz)
        start_request_review(request_obj=self.req, actor=self.manager)

    def test_approving_request_triggers_domain_service(self):
        approve_request(request_obj=self.req, actor=self.manager)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.approval_status, "approved")


class RequestIDORAndScopeTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری درخواست")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری درخواست")
        sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری درخواست")

        babol_network = HealthNetwork.objects.create(county=babol, name="شبکه بابل درخواست")
        babol_center = HealthCenter.objects.create(network=babol_network, name="مرکز بابل درخواست")
        babol_house = HealthHouse.objects.create(center=babol_center, name="خانه بابل درخواست")

        self.sari_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        babol_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=babol)

        sari_requester = User.objects.create_user(username="req_sari_user", password="pass12345")
        babol_requester = User.objects.create_user(username="req_babol_user", password="pass12345")

        self.sari_request = Request.objects.create(
            requester=sari_requester, request_type=RequestType.OTHER, title="درخواست ساری", scope=self.sari_scope,
        )
        self.babol_request = Request.objects.create(
            requester=babol_requester, request_type=RequestType.OTHER, title="درخواست بابل", scope=babol_scope,
        )

        self.other_user_a = User.objects.create_user(username="req_stranger_a", password="pass12345")

        self.reviewer = User.objects.create_user(username="req_sari_reviewer", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="request.view"))
        RoleAssignment.objects.create(
            user=self.reviewer, role=role, access_scope=self.sari_scope, start_date=timezone.localdate(),
        )
        # طبق طراحی Authorization Engine (گام ۰۶): برای این‌که Scope واقعاً
        # containment داشته باشد، Reviewer باید حداقل یک EmploymentAssignment
        # فعال در همان محدوده داشته باشد — وگرنه هر دو Scope «بدون HealthHouse»
        # تلقی می‌شوند و پیش‌فرض به «مجاز» می‌رود.
        EmploymentAssignment.objects.create(
            user=self.reviewer, health_house=sari_house, start_date=timezone.localdate(), is_primary=True,
        )
        # و برای این‌که واقعاً یک تفاوت Scope داشته باشیم، هر Request را هم
        # به یک EmploymentAssignment واقعی (از طریق content_object) وصل می‌کنیم:
        self.sari_assignment = EmploymentAssignment.objects.create(
            user=sari_requester, health_house=sari_house, start_date=timezone.localdate(), is_primary=True,
        )
        self.babol_assignment = EmploymentAssignment.objects.create(
            user=babol_requester, health_house=babol_house, start_date=timezone.localdate(), is_primary=True,
        )

    def test_owner_can_view_own_request(self):
        self.client.login(username="req_sari_user", password="pass12345")
        response = self.client.get(reverse("requests_portal:detail", kwargs={"pk": self.sari_request.pk}))
        self.assertEqual(response.status_code, 200)

    def test_idor_other_user_cannot_view_portal_request(self):
        self.client.login(username="req_stranger_a", password="pass12345")
        response = self.client.get(reverse("requests_portal:detail", kwargs={"pk": self.sari_request.pk}))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_access_portal_list(self):
        response = self.client.get(reverse("requests_portal:list"))
        self.assertEqual(response.status_code, 302)

    def test_reviewer_can_view_in_scope_request(self):
        self.client.login(username="req_sari_reviewer", password="pass12345")
        response = self.client.get(reverse("requests_mgmt:detail", kwargs={"pk": self.sari_request.pk}))
        self.assertEqual(response.status_code, 200)

    def test_reviewer_cannot_view_out_of_scope_request(self):
        self.client.login(username="req_sari_reviewer", password="pass12345")
        response = self.client.get(reverse("requests_mgmt:detail", kwargs={"pk": self.babol_request.pk}))
        self.assertEqual(response.status_code, 403)

class RequestConcurrencyTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(username="req_concurrency_user", password="pass12345")
        self.manager = User.objects.create_user(username="req_concurrency_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(
            Permission.objects.get(code="request.review"),
            Permission.objects.get(code="request.approve"),
        )
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=timezone.localdate(),
        )
        self.req = create_request(
            requester=self.requester, request_type=RequestType.OTHER, title="تست همزمانی", scope=scope,
        )
        submit_request(request_obj=self.req, actor=self.requester)
        start_request_review(request_obj=self.req, actor=self.manager)

    def test_double_approval_second_call_fails_gracefully(self):
        """بعد از اولین Approve موفق، تلاش دوم باید با ValidationError رد شود، نه کرش."""
        approve_request(request_obj=self.req, actor=self.manager)
        with self.assertRaises(ValidationError):
            approve_request(request_obj=self.req, actor=self.manager)


class RequestNotificationTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(username="req_notif_user", password="pass12345")
        self.manager = User.objects.create_user(username="req_notif_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(
            Permission.objects.get(code="request.review"),
            Permission.objects.get(code="request.approve"),
        )
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=timezone.localdate(),
        )
        self.req = create_request(
            requester=self.requester, request_type=RequestType.OTHER, title="تست اعلان", scope=scope,
        )
        submit_request(request_obj=self.req, actor=self.requester)
        start_request_review(request_obj=self.req, actor=self.manager)

    def test_requester_notified_on_approval(self):
        from apps.notifications.models import Notification

        approve_request(request_obj=self.req, actor=self.manager)
        self.assertTrue(Notification.objects.filter(recipient=self.requester).exists())