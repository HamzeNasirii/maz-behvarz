import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.board.choices import BoardPosition, BoardStatus
from apps.board.models import Board, BoardMembership
from apps.board.services import (
    activate_board,
    add_board_member,
    archive_board,
    create_board,
    end_board,
    remove_board_member,
    suspend_board,
)
from apps.organization.models import County, Province

User = get_user_model()


class BoardPeriodLifecycleTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="board_period_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(
            Permission.objects.get(code="board.create"),
            Permission.objects.get(code="board.update"),
            Permission.objects.get(code="board.delete"),
            Permission.objects.get(code="board.manage_members"),
            Permission.objects.get(code="board.view"),
        )
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

    def test_create_board(self):
        board = create_board(
            created_by=self.manager, start_date=datetime.date(2025, 3, 21),
        )
        self.assertEqual(board.status, BoardStatus.DRAFT)

    def test_full_lifecycle_to_archive(self):
        board = create_board(created_by=self.manager, start_date=datetime.date.today())
        activate_board(board=board, actor=self.manager)
        suspend_board(board=board, actor=self.manager, reason="بازبینی")
        end_board(board=board, actor=self.manager)
        archive_board(board=board, actor=self.manager)
        board.refresh_from_db()
        self.assertEqual(board.status, BoardStatus.ARCHIVED)

    def test_invalid_transition_blocked(self):
        board = create_board(created_by=self.manager, start_date=datetime.date.today())
        board.status = BoardStatus.ARCHIVED
        board.save()
        with self.assertRaises(ValidationError):
            activate_board(board=board, actor=self.manager)

    def test_unauthorized_cannot_create(self):
        stranger = User.objects.create_user(username="board_stranger", password="pass12345")
        with self.assertRaises(PermissionDenied):
            create_board(created_by=stranger, start_date=datetime.date.today())

    def test_historical_boards_preserved(self):
        board1 = create_board(created_by=self.manager, start_date=datetime.date(2022, 1, 1))
        board2 = create_board(created_by=self.manager, start_date=datetime.date(2025, 1, 1))
        activate_board(board=board2, actor=self.manager)
        self.assertEqual(Board.objects.count(), 2)
        self.assertTrue(Board.objects.filter(pk=board1.pk).exists())


class BoardMembershipManagementTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="board_member_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="board.manage_members"))
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=datetime.date.today(),
        )
        self.board = Board.objects.create(name="هیئت‌مدیره تست عضویت", start_date=datetime.date.today())
        self.target = User.objects.create_user(username="board_target_new", password="pass12345")

    def test_add_member_to_board(self):
        membership = add_board_member(
            board=self.board, user=self.target, position=BoardPosition.MEMBER,
            added_by=self.manager, start_date=datetime.date.today(),
        )
        self.assertEqual(membership.board, self.board)

    def test_self_add_blocked(self):
        with self.assertRaises(PermissionDenied):
            add_board_member(
                board=self.board, user=self.manager, position=BoardPosition.CHAIRMAN,
                added_by=self.manager, start_date=datetime.date.today(),
            )

    def test_remove_member_preserves_history(self):
        membership = BoardMembership.objects.create(
            board=self.board, user=self.target, position=BoardPosition.MEMBER,
            start_date=datetime.date(2020, 1, 1),
        )
        remove_board_member(membership=membership, removed_by=self.manager, end_date=datetime.date.today())
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)
        self.assertTrue(BoardMembership.objects.filter(pk=membership.pk).exists())

    def test_multiple_responsibilities_board_committee_representative(self):
        """User A: County Representative (County A) + Committee Chair (Province) + Board Member"""
        from apps.committees.models import Committee

        province = self.manager.role_assignments.first().access_scope.county.province
        province_scope = AccessScope.objects.create(scope_type=AccessScopeType.PROVINCE, province=province)
        committee = Committee.objects.create(name="کمیته چندمسئولیتی")
        committee_scope = AccessScope.objects.create(scope_type=AccessScopeType.COMMITTEE, committee=committee)

        county_scope = AccessScope.objects.create(
            scope_type=AccessScopeType.COUNTY, county=self.manager.role_assignments.first().access_scope.county,
        )
        RoleAssignment.objects.create(
            user=self.target, role=Role.objects.get(code="COUNTY_REPRESENTATIVE"),
            access_scope=county_scope, start_date=datetime.date.today(),
        )
        RoleAssignment.objects.create(
            user=self.target, role=Role.objects.get(code="COMMITTEE_MANAGER"),
            access_scope=committee_scope, start_date=datetime.date.today(),
        )
        BoardMembership.objects.create(
            board=self.board, user=self.target, position=BoardPosition.MEMBER, start_date=datetime.date.today(),
        )

        self.assertEqual(RoleAssignment.objects.for_user(self.target).active().count(), 3)
        self.assertEqual(BoardMembership.objects.filter(user=self.target, is_active=True).count(), 1)


class BoardManagementIDORTests(TestCase):
    def setUp(self):
        self.board_a = Board.objects.create(name="هیئت‌مدیره IDOR A", start_date=datetime.date.today())
        self.board_b = Board.objects.create(name="هیئت‌مدیره IDOR B", start_date=datetime.date.today())

        self.viewer = User.objects.create_user(username="board_idor_viewer", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="board.view"))
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.viewer, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

    def test_authenticated_user_with_permission_can_view(self):
        self.client.login(username="board_idor_viewer", password="pass12345")
        response = self.client.get(reverse("board_mgmt:detail", kwargs={"pk": self.board_a.pk}))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_cannot_access_list(self):
        response = self.client.get(reverse("board_mgmt:list"))
        self.assertEqual(response.status_code, 302)

    def test_user_without_permission_gets_403(self):
        stranger = User.objects.create_user(username="board_view_stranger", password="pass12345")
        self.client.login(username="board_view_stranger", password="pass12345")
        response = self.client.get(reverse("board_mgmt:list"))
        self.assertEqual(response.status_code, 403)


class RepresentativeScopeAndPublicTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        self.babol = County.objects.create(province=province, name="بابل")

        self.sari_rep_user = User.objects.create_user(username="sari_rep_user", password="pass12345")
        sari_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        self.sari_assignment = RoleAssignment.objects.create(
            user=self.sari_rep_user, role=Role.objects.get(code="COUNTY_REPRESENTATIVE"),
            access_scope=sari_scope, start_date=datetime.date.today(), is_public_visible=True,
        )

        self.babol_rep_user = User.objects.create_user(username="babol_rep_user", password="pass12345")
        babol_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.babol)
        RoleAssignment.objects.create(
            user=self.babol_rep_user, role=Role.objects.get(code="COUNTY_REPRESENTATIVE"),
            access_scope=babol_scope, start_date=datetime.date.today(), is_public_visible=False,
        )

    def test_county_representatives_selector_scoped_to_county(self):
        from apps.authorization.selectors import county_representatives

        reps = county_representatives(self.sari)
        self.assertEqual(reps.count(), 1)
        self.assertEqual(reps.first().user, self.sari_rep_user)

    def test_only_public_visible_representative_shown(self):
        response = self.client.get(reverse("public_content:representatives"))
        self.assertContains(response, "sari_rep_user")
        self.assertNotContains(response, "babol_rep_user")

    def test_expired_representative_no_longer_active(self):
        self.sari_assignment.start_date = datetime.date.today() - datetime.timedelta(days=10)
        self.sari_assignment.end_date = datetime.date.today() - datetime.timedelta(days=1)
        self.sari_assignment.is_active = False
        self.sari_assignment.save()
        from apps.authorization.selectors import county_representatives

        self.assertEqual(county_representatives(self.sari).count(), 0)


class BoardPublicVisibilityTests(TestCase):
    def test_private_board_excluded_from_public_selector(self):
        from apps.board.selectors import public_boards

        Board.objects.create(
            name="هیئت‌مدیره خصوصی جدید", start_date=datetime.date.today(),
            status=BoardStatus.ACTIVE, is_public_visible=False,
        )
        self.assertFalse(public_boards().filter(name="هیئت‌مدیره خصوصی جدید").exists())

    def test_public_active_board_in_public_selector(self):
        from apps.board.selectors import public_boards

        Board.objects.create(
            name="هیئت‌مدیره عمومی جدید", start_date=datetime.date.today(),
            status=BoardStatus.ACTIVE, is_public_visible=True,
        )
        self.assertTrue(public_boards().filter(name="هیئت‌مدیره عمومی جدید").exists())


class BoardAutoNamingTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="board_naming_manager", password="pass12345", is_staff=True)

    def test_first_board_named_dore_1(self):
        board = create_board(created_by=self.manager, start_date=datetime.date.today())
        self.assertEqual(board.name, "دوره 1")

    def test_second_board_named_dore_2(self):
        create_board(created_by=self.manager, start_date=datetime.date.today())
        board2 = create_board(created_by=self.manager, start_date=datetime.date.today())
        self.assertEqual(board2.name, "دوره 2")


class BoardInlineCreationTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="board_inline_manager", password="pass12345", is_staff=True)

    def test_create_board_via_list_view_post(self):
        self.client.login(username="board_inline_manager", password="pass12345")
        response = self.client.post(reverse("board_mgmt:list"), {
            "description": "", "start_date": "1404/06/15", "end_date": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Board.objects.filter(name="دوره 1").exists())

    def test_member_count_shown_in_list(self):
        board = create_board(created_by=self.manager, start_date=datetime.date.today())
        activate_board(board=board, actor=self.manager)
        target = User.objects.create_user(username="board_count_target", password="pass12345")
        BoardMembership.objects.create(
            board=board, user=target, position=BoardPosition.MEMBER, start_date=datetime.date.today(),
        )
        self.client.login(username="board_inline_manager", password="pass12345")
        response = self.client.get(reverse("board_mgmt:list"))
        self.assertEqual(response.context["boards"].get(pk=board.pk).member_count, 1)

