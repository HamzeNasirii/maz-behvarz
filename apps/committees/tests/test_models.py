import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.committees.models import Committee, CommitteeMembership

User = get_user_model()


class CommitteeMembershipTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="committee_user", password="pass12345")
        self.committee = Committee.objects.create(name="کمیته آموزش")

    def test_committee_membership_creation(self):
        membership = CommitteeMembership.objects.create(
            committee=self.committee, user=self.user, start_date=datetime.date.today(),
        )
        self.assertTrue(membership.is_active)

    def test_only_one_active_membership_per_user_per_committee(self):
        CommitteeMembership.objects.create(
            committee=self.committee, user=self.user, start_date=datetime.date.today(),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CommitteeMembership.objects.create(
                    committee=self.committee, user=self.user, start_date=datetime.date.today(),
                )

class CommitteePublicVisibilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="committee_vis_user", password="pass12345")

    def test_committee_and_membership_default_not_public(self):
        committee = Committee.objects.create(name="کمیته تست عمومی")
        self.assertFalse(committee.is_public_visible)

        membership = CommitteeMembership.objects.create(
            committee=committee, user=self.user, start_date=datetime.date.today(),
        )
        self.assertFalse(membership.is_public_visible)