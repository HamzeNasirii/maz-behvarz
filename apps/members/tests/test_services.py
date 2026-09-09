import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.members.models import Member, MembershipPeriod
from apps.members.services import end_membership_period, renew_membership, start_membership_period

User = get_user_model()


class MembershipServiceTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="member_svc", password="pass12345")
        self.member = Member.objects.create(user=user)

    def test_start_membership_period(self):
        period = start_membership_period(member=self.member, start_date=datetime.date(2024, 1, 1))
        self.assertTrue(period.is_active)
        self.assertIsNone(period.end_date)

    def test_end_membership_period(self):
        period = start_membership_period(member=self.member, start_date=datetime.date(2024, 1, 1))
        end_membership_period(
            membership_period=period, end_date=datetime.date(2024, 12, 31), reason="عدم پرداخت"
        )
        period.refresh_from_db()
        self.assertFalse(period.is_active)
        self.assertEqual(period.end_date, datetime.date(2024, 12, 31))

    def test_renew_membership_closes_previous_and_opens_new(self):
        start_membership_period(member=self.member, start_date=datetime.date(2024, 1, 1))
        new_period = renew_membership(member=self.member, new_start_date=datetime.date(2025, 1, 1))

        self.assertEqual(MembershipPeriod.objects.for_member(self.member).count(), 2)
        self.assertTrue(new_period.is_active)
        self.assertEqual(
            MembershipPeriod.objects.for_member(self.member).active().count(), 1
        )


from django.core.exceptions import PermissionDenied

from apps.authorization.choices import AccessScopeType, ApprovalStatus
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.members.services import approve_member, reject_member
from apps.organization.models import County, Province


class MemberApprovalTests(TestCase):
    def setUp(self):
        creator = User.objects.create_user(username="registrar", password="pass12345")
        applicant = User.objects.create_user(username="applicant", password="pass12345")
        self.member = Member.objects.create(user=applicant, registered_by=creator)

        approver = User.objects.create_user(username="approver", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="member.approve"))
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=approver, role=role, access_scope=scope, start_date=datetime.date.today(),
        )
        self.creator = creator
        self.approver = approver

    def test_approve_member_success(self):
        approve_member(member=self.member, approved_by=self.approver)
        self.member.refresh_from_db()
        self.assertEqual(self.member.approval_status, ApprovalStatus.APPROVED)

    def test_creator_cannot_approve_own_registration(self):
        # به creator هم دسترسی member.approve بده تا فقط قاعده‌ی creator!=approver رو تست کنیم
        role = Role.objects.get(code="BEHVARZ")
        with self.assertRaises(PermissionDenied):
            approve_member(member=self.member, approved_by=self.creator)

    def test_user_without_permission_cannot_approve(self):
        stranger = User.objects.create_user(username="stranger2", password="pass12345")
        with self.assertRaises(PermissionDenied):
            approve_member(member=self.member, approved_by=stranger)

    def test_reject_member_records_reason(self):
        reject_member(member=self.member, rejected_by=self.approver, reason="مدارک ناقص")
        self.member.refresh_from_db()
        self.assertEqual(self.member.approval_status, ApprovalStatus.REJECTED)
        self.assertEqual(self.member.rejection_reason, "مدارک ناقص")