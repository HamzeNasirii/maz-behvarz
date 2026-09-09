import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Role, RoleAssignment
from apps.board.choices import BoardPosition
from apps.board.models import Board, BoardMembership
from apps.members.choices import FeeChangeStatus
from apps.members.models import Member, MembershipFee
from apps.members.services import (
    approve_fee_change,
    cancel_fee_change,
    propose_fee_delete,
    propose_fee_edit,
    reject_fee_change,
)
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

User = get_user_model()


class FeeChangeWorkflowTestsBase(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران فی تست")
        county = County.objects.create(province=province, name="ساری فی تست")
        network = HealthNetwork.objects.create(county=county, name="شبکه فی تست")
        center = HealthCenter.objects.create(network=network, name="مرکز فی تست")
        house = HealthHouse.objects.create(center=center, name="خانه فی تست")

        member_user = User.objects.create_user(username="fee_flow_member", password="pass12345")
        self.member = Member.objects.create(user=member_user)
        self.fee = MembershipFee.objects.create(member=self.member, amount=500000, due_date=timezone.localdate())

        province_scope = AccessScope.objects.create(scope_type=AccessScopeType.PROVINCE, province=province)
        board_role = Role.objects.get(code="BOARD_MEMBER")

        self.board = Board.objects.create(name="دوره فی تست", start_date=timezone.localdate())

        self.treasurer = User.objects.create_user(username="fee_flow_treasurer", password="pass12345")
        BoardMembership.objects.create(
            board=self.board, user=self.treasurer, position=BoardPosition.TREASURER, start_date=timezone.localdate(),
        )
        RoleAssignment.objects.filter(user=self.treasurer, role=board_role).delete()
        RoleAssignment.objects.create(
            user=self.treasurer, role=board_role, access_scope=province_scope, start_date=timezone.localdate(),
        )

        self.chairman = User.objects.create_user(username="fee_flow_chairman", password="pass12345")
        BoardMembership.objects.create(
            board=self.board, user=self.chairman, position=BoardPosition.CHAIRMAN, start_date=timezone.localdate(),
        )
        RoleAssignment.objects.filter(user=self.chairman, role=board_role).delete()
        RoleAssignment.objects.create(
            user=self.chairman, role=board_role, access_scope=province_scope, start_date=timezone.localdate(),
        )

        self.plain_board_member = User.objects.create_user(username="fee_flow_plain", password="pass12345")
        BoardMembership.objects.create(
            board=self.board, user=self.plain_board_member, position=BoardPosition.MEMBER, start_date=timezone.localdate(),
        )


class TwoPersonRuleTests(FeeChangeWorkflowTestsBase):
    """⚠️ مهم‌ترین تست‌های این فایل: قانون «دو نفره» در تصمیمات مالی."""

    def test_treasurer_proposes_chairman_approves_succeeds(self):
        cr = propose_fee_edit(
            fee=self.fee, proposed_by=self.treasurer,
            new_amount=600000, new_due_date=timezone.localdate(), reason="اصلاح مبلغ",
        )
        approve_fee_change(change_request=cr, actor=self.chairman)
        cr.refresh_from_db()
        self.assertEqual(cr.status, FeeChangeStatus.APPROVED)

    def test_chairman_proposes_treasurer_approves_succeeds(self):
        cr = propose_fee_edit(
            fee=self.fee, proposed_by=self.chairman,
            new_amount=600000, new_due_date=timezone.localdate(), reason="اصلاح مبلغ",
        )
        approve_fee_change(change_request=cr, actor=self.treasurer)
        cr.refresh_from_db()
        self.assertEqual(cr.status, FeeChangeStatus.APPROVED)

    def test_chairman_proposes_another_chairman_like_role_without_treasurer_fails(self):
        """
        اگر نه پیشنهاددهنده نه تصمیم‌گیرنده خزانه‌دار نباشند، باید رد شود
        — حتی اگر هردو از سمت‌های تصمیم‌گیر (رئیس/دبیر) باشند.
        """
        secretary = User.objects.create_user(username="fee_flow_secretary", password="pass12345")
        BoardMembership.objects.create(
            board=self.board, user=secretary, position=BoardPosition.SECRETARY, start_date=timezone.localdate(),
        )
        cr = propose_fee_edit(
            fee=self.fee, proposed_by=self.chairman,
            new_amount=600000, new_due_date=timezone.localdate(), reason="اصلاح مبلغ",
        )
        with self.assertRaises(PermissionDenied):
            approve_fee_change(change_request=cr, actor=secretary)

    def test_plain_board_member_cannot_even_propose(self):
        with self.assertRaises(PermissionDenied):
            propose_fee_edit(
                fee=self.fee, proposed_by=self.plain_board_member,
                new_amount=600000, new_due_date=timezone.localdate(), reason="تلاش غیرمجاز",
            )


class SelfApprovalPreventionTests(FeeChangeWorkflowTestsBase):
    def test_treasurer_cannot_approve_own_proposal(self):
        cr = propose_fee_edit(
            fee=self.fee, proposed_by=self.treasurer,
            new_amount=600000, new_due_date=timezone.localdate(), reason="اصلاح مبلغ",
        )
        with self.assertRaises(PermissionDenied):
            approve_fee_change(change_request=cr, actor=self.treasurer)

    def test_treasurer_cannot_reject_own_proposal(self):
        cr = propose_fee_edit(
            fee=self.fee, proposed_by=self.treasurer,
            new_amount=600000, new_due_date=timezone.localdate(), reason="اصلاح مبلغ",
        )
        with self.assertRaises(PermissionDenied):
            reject_fee_change(change_request=cr, actor=self.treasurer)


class FeeChangeCancelTests(FeeChangeWorkflowTestsBase):
    def test_proposer_can_cancel_own_request(self):
        cr = propose_fee_delete(fee=self.fee, proposed_by=self.treasurer, reason="اشتباه بود")
        cancel_fee_change(change_request=cr, actor=self.treasurer)
        cr.refresh_from_db()
        self.assertEqual(cr.status, FeeChangeStatus.CANCELLED)

    def test_other_user_cannot_cancel_someone_elses_request(self):
        cr = propose_fee_delete(fee=self.fee, proposed_by=self.treasurer, reason="اشتباه بود")
        with self.assertRaises(PermissionDenied):
            cancel_fee_change(change_request=cr, actor=self.chairman)

    def test_cannot_cancel_already_decided_request(self):
        cr = propose_fee_edit(
            fee=self.fee, proposed_by=self.treasurer,
            new_amount=600000, new_due_date=timezone.localdate(), reason="اصلاح مبلغ",
        )
        approve_fee_change(change_request=cr, actor=self.chairman)
        with self.assertRaises(ValidationError):
            cancel_fee_change(change_request=cr, actor=self.treasurer)


class FeeChangeEffectTests(FeeChangeWorkflowTestsBase):
    def test_approved_edit_actually_changes_fee(self):
        new_date = timezone.localdate() + datetime.timedelta(days=30)
        cr = propose_fee_edit(
            fee=self.fee, proposed_by=self.treasurer, new_amount=750000, new_due_date=new_date, reason="اصلاح",
        )
        approve_fee_change(change_request=cr, actor=self.chairman)
        self.fee.refresh_from_db()
        self.assertEqual(int(self.fee.amount), 750000)
        self.assertEqual(self.fee.due_date, new_date)

    def test_approved_delete_actually_deletes_fee(self):
        fee_pk = self.fee.pk
        cr = propose_fee_delete(fee=self.fee, proposed_by=self.treasurer, reason="اشتباه ثبت شده بود")
        approve_fee_change(change_request=cr, actor=self.chairman)
        self.assertFalse(MembershipFee.objects.filter(pk=fee_pk).exists())

    def test_rejected_edit_does_not_change_fee(self):
        original_amount = self.fee.amount
        cr = propose_fee_edit(
            fee=self.fee, proposed_by=self.treasurer, new_amount=999999, new_due_date=timezone.localdate(), reason="اصلاح",
        )
        reject_fee_change(change_request=cr, actor=self.chairman)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.amount, original_amount)