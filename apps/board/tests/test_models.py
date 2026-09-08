import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.board.choices import BoardPosition
from apps.board.models import BoardMembership

User = get_user_model()


class BoardMembershipTests(TestCase):
    def setUp(self):
        self.chairman = User.objects.create_user(username="chairman1", password="pass12345")
        self.other_user = User.objects.create_user(username="board_user2", password="pass12345")

    def test_board_membership_creation(self):
        membership = BoardMembership.objects.create(
            user=self.chairman, position=BoardPosition.CHAIRMAN, start_date=datetime.date.today(),
        )
        self.assertTrue(membership.is_active)

    def test_only_one_active_chairman_allowed(self):
        BoardMembership.objects.create(
            user=self.chairman, position=BoardPosition.CHAIRMAN, start_date=datetime.date.today(),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BoardMembership.objects.create(
                    user=self.other_user, position=BoardPosition.CHAIRMAN,
                    start_date=datetime.date.today(),
                )

    def test_multiple_plain_members_allowed(self):
        BoardMembership.objects.create(
            user=self.chairman, position=BoardPosition.MEMBER, start_date=datetime.date.today(),
        )
        BoardMembership.objects.create(
            user=self.other_user, position=BoardPosition.MEMBER, start_date=datetime.date.today(),
        )
        self.assertEqual(BoardMembership.objects.filter(is_active=True).count(), 2)

    def test_user_cannot_have_two_simultaneous_active_positions(self):
        BoardMembership.objects.create(
            user=self.chairman, position=BoardPosition.CHAIRMAN, start_date=datetime.date.today(),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BoardMembership.objects.create(
                    user=self.chairman, position=BoardPosition.SECRETARY,
                    start_date=datetime.date.today(),
                )