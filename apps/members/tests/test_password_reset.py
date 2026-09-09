from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reset_user", password="oldpass12345", email="reset@example.com"
        )

    def test_password_reset_request_returns_200(self):
        response = self.client.get(reverse("password_reset"))
        self.assertEqual(response.status_code, 200)

    def test_password_reset_sends_email(self):
        from django.core import mail

        response = self.client.post(reverse("password_reset"), {"email": "reset@example.com"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_password_reset_confirm_with_valid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.get(
            reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
        )
        self.assertEqual(response.status_code, 302)  # Redirect به فرم واقعی با توکن set-password

    def test_password_reset_confirm_with_invalid_token_shows_invalid_link(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(
            reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": "invalid-token"})
        )
        self.assertContains(response, "نامعتبر")