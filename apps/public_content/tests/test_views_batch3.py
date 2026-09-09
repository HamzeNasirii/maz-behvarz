import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.board.choices import BoardPosition
from apps.board.models import BoardMembership
from apps.committees.models import Committee, CommitteeMembership

User = get_user_model()


class BoardPageTests(TestCase):
    def test_only_public_visible_members_shown(self):
        public_user = User.objects.create_user(username="board_public", password="pass12345")
        private_user = User.objects.create_user(username="board_private", password="pass12345")

        BoardMembership.objects.create(
            user=public_user, position=BoardPosition.CHAIRMAN,
            start_date=datetime.date.today(), is_public_visible=True,
        )
        BoardMembership.objects.create(
            user=private_user, position=BoardPosition.SECRETARY,
            start_date=datetime.date.today(), is_public_visible=False,
        )

        response = self.client.get(reverse("public_content:board"))
        self.assertContains(response, "board_public")
        self.assertNotContains(response, "board_private")


class CommitteesPageTests(TestCase):
    def test_only_public_committees_shown(self):
        Committee.objects.create(name="کمیته عمومی", is_active=True, is_public_visible=True)
        Committee.objects.create(name="کمیته خصوصی", is_active=True, is_public_visible=False)

        response = self.client.get(reverse("public_content:committees"))
        self.assertContains(response, "کمیته عمومی")
        self.assertNotContains(response, "کمیته خصوصی")


class AboutPagesTests(TestCase):
    def test_about_history_returns_200(self):
        self.assertEqual(self.client.get(reverse("website:about_history")).status_code, 200)

    def test_about_mission_returns_200(self):
        self.assertEqual(self.client.get(reverse("website:about_mission")).status_code, 200)

    def test_about_objectives_returns_200(self):
        self.assertEqual(self.client.get(reverse("website:about_objectives")).status_code, 200)

    def test_organizational_structure_returns_200(self):
        response = self.client.get(reverse("website:about_organizational_structure"))
        self.assertEqual(response.status_code, 200)

    def test_privacy_page_returns_200(self):
        self.assertEqual(self.client.get(reverse("website:privacy")).status_code, 200)

    def test_terms_page_returns_200(self):
        self.assertEqual(self.client.get(reverse("website:terms")).status_code, 200)


class HomePageWithContentTests(TestCase):
    def test_home_still_returns_200_with_new_context(self):
        response = self.client.get(reverse("website:home"))
        self.assertEqual(response.status_code, 200)