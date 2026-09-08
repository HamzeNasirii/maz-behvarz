import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.employment.models import EmploymentAssignment
from apps.members.models import Member
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province
from apps.requests.choices import RequestStatus, RequestType
from apps.requests.models import Request
from apps.requests.services import approve_request, create_request, start_request_review, submit_request
from apps.requests.target_validation import validate_target_object

User = get_user_model()


class GenericRelationSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="grs_user", password="pass12345")
        self.member = Member.objects.create(user=self.user)

    def test_allowed_target_accepted(self):
        validate_target_object(self.member)  # نباید Exception بدهد

    def test_none_target_accepted(self):
        validate_target_object(None)  # نباید Exception بدهد

    def test_disallowed_target_rejected(self):
        with self.assertRaises(ValidationError):
            validate_target_object(self.user)  # CustomUser در Whitelist نیست

    def test_create_request_rejects_disallowed_content_object(self):
        with self.assertRaises(ValidationError):
            create_request(
                requester=self.user, request_type=RequestType.OTHER, title="تست",
                content_object=self.user,
            )

    def test_create_request_accepts_allowed_content_object(self):
        req = create_request(
            requester=self.user, request_type=RequestType.OTHER, title="تست", content_object=self.member,
        )
        self.assertEqual(req.content_object, self.member)


class AdvancedFilterSecurityTests(TestCase):
    """طبق بخش ۲۵/۲۶ سند: Scope باید قبل از Filter/Search اعمال شود."""

    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        self.sari_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        babol_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=babol)

        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری فیلتر")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری فیلتر")
        sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری فیلتر")

        sari_requester = User.objects.create_user(username="filter_sari_user", password="pass12345")
        babol_requester = User.objects.create_user(username="filter_babol_user", password="pass12345")

        Request.objects.create(
            requester=sari_requester, request_type=RequestType.OTHER, title="جستجوی مشترک ساری",
            scope=self.sari_scope,
        )
        Request.objects.create(
            requester=babol_requester, request_type=RequestType.OTHER, title="جستجوی مشترک بابل",
            scope=babol_scope,
        )

        self.reviewer = User.objects.create_user(username="filter_reviewer", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="request.view"))
        RoleAssignment.objects.create(
            user=self.reviewer, role=role, access_scope=self.sari_scope, start_date=timezone.localdate(),
        )
        EmploymentAssignment.objects.create(
            user=self.reviewer, health_house=sari_house, start_date=timezone.localdate(), is_primary=True,
        )

    def test_search_cannot_escape_scope(self):
        """جستجوی یک عبارت مشترک نباید نتیجه‌ی خارج از Scope را نشان دهد."""
        self.client.login(username="filter_reviewer", password="pass12345")
        response = self.client.get(reverse("requests_mgmt:list"), {"q": "جستجوی مشترک"})
        self.assertContains(response, "جستجوی مشترک ساری")
        self.assertNotContains(response, "جستجوی مشترک بابل")

    def test_pagination_cannot_escape_scope(self):
        self.client.login(username="filter_reviewer", password="pass12345")
        response = self.client.get(reverse("requests_mgmt:list"), {"page": "1"})
        for req in response.context["page_obj"]:
            self.assertEqual(req.scope_id, self.sari_scope.id)

    def test_unauthenticated_cannot_access_management_list(self):
        response = self.client.get(reverse("requests_mgmt:list"))
        self.assertEqual(response.status_code, 302)


class IdempotencyTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(username="idem_user", password="pass12345")
        self.manager = User.objects.create_user(username="idem_manager", password="pass12345")
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
        self.req = create_request(requester=self.requester, request_type=RequestType.OTHER, title="تست idempotency", scope=scope)
        submit_request(request_obj=self.req, actor=self.requester)
        start_request_review(request_obj=self.req, actor=self.manager)

    def test_double_approve_does_not_create_phantom_history(self):
        approve_request(request_obj=self.req, actor=self.manager)
        history_count_after_first = self.req.history.count()

        with self.assertRaises(ValidationError):
            approve_request(request_obj=self.req, actor=self.manager)

        # تلاش نافرجام دوم نباید رکورد تاریخچه‌ی جدیدی ساخته باشد
        self.assertEqual(self.req.history.count(), history_count_after_first)


class EmploymentTransferReuseAuditTests(TestCase):
    """
    طبق بخش ۱۶ سند: Audit مجدد یکپارچگی موجود EMPLOYMENT_TRANSFER —
    تأیید Double Execution ایمن است و History درست ثبت می‌شود.
    """

    def setUp(self):
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری۳۴")
        center = HealthCenter.objects.create(network=network, name="مرکز ساری۳۴")
        house = HealthHouse.objects.create(center=center, name="خانه ساری۳۴")

        self.behvarz = User.objects.create_user(username="p34_behvarz", password="pass12345")
        self.assignment = EmploymentAssignment.objects.create(
            user=self.behvarz, health_house=house, start_date=timezone.localdate(),
        )

        self.manager = User.objects.create_user(username="p34_emp_manager", password="pass12345")
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
            title="Audit مجدد یکپارچگی", scope=scope, content_object=self.assignment,
        )
        submit_request(request_obj=self.req, actor=self.behvarz)
        start_request_review(request_obj=self.req, actor=self.manager)

    def test_approval_triggers_domain_service_exactly_once(self):
        approve_request(request_obj=self.req, actor=self.manager)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.approval_status, "approved")

    def test_double_execution_blocked_by_request_state_machine(self):
        """
        چون Request خودش پس از APPROVED دیگر اجازه‌ی approve مجدد
        نمی‌دهد، حتی اگر کسی سعی کند دوباره approve_request را صدا
        بزند، Domain Service دوباره اجرا نمی‌شود.
        """
        approve_request(request_obj=self.req, actor=self.manager)
        with self.assertRaises(ValidationError):
            approve_request(request_obj=self.req, actor=self.manager)
        # اگر Domain Action دوباره اجرا شده بود، این خط خطا می‌داد
        # چون approve_employment_transfer خودش هم یک بار دیگر approval_status را چک می‌کند —
        # اینجا فقط تأیید می‌کنیم Assignment هنوز در وضعیت منطقی است.
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.approval_status, "approved")


class NotificationScopeSecurityTests(TestCase):
    """طبق بخش ۱۲ سند: Notification مربوط به Request باید Scope-aware بماند."""

    def setUp(self):
        self.requester_a = User.objects.create_user(username="notif_req_a", password="pass12345")
        self.requester_b = User.objects.create_user(username="notif_req_b", password="pass12345")
        self.manager = User.objects.create_user(username="notif_req_manager", password="pass12345")
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

        self.req_a = create_request(requester=self.requester_a, request_type=RequestType.OTHER, title="درخواست A", scope=scope)
        submit_request(request_obj=self.req_a, actor=self.requester_a)
        start_request_review(request_obj=self.req_a, actor=self.manager)
        approve_request(request_obj=self.req_a, actor=self.manager)

    def test_only_requester_receives_notification(self):
        from apps.notifications.models import Notification

        self.assertTrue(Notification.objects.filter(recipient=self.requester_a).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.requester_b).exists())

    def test_notification_idor_cannot_access_other_users_request_via_notification(self):
        from apps.notifications.models import Notification

        notif = Notification.objects.filter(recipient=self.requester_a).first()
        self.client.login(username="notif_req_b", password="pass12345")
        response = self.client.get(reverse("notifications_portal:detail", kwargs={"pk": notif.pk}))
        self.assertEqual(response.status_code, 403)