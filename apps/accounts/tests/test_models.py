from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class CustomUserTests(TestCase):
    def test_auth_user_model_is_custom_user(self):
        """Test 2: CustomUser exists and AUTH_USER_MODEL points to it."""
        self.assertEqual(User.__name__, "CustomUser")

    def test_user_creation(self):
        user = User.objects.create_user(
            username="behvarz1", password="a-strong-pass-123"
        )
        self.assertTrue(user.pk)
        self.assertTrue(user.check_password("a-strong-pass-123"))

    def test_user_has_no_direct_health_house_field(self):
        """Test 13: User نباید مستقیم به HealthHouse وصل باشد."""
        field_names = [f.name for f in User._meta.get_fields()]
        self.assertNotIn("health_house", field_names)