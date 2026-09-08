from django.test import Client, TestCase, override_settings


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class ErrorPagesTests(TestCase):
    def setUp(self):
        self.client = Client(raise_request_exception=False)

    def test_404_page_renders_custom_template(self):
        response = self.client.get("/nonexistent-page/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "صفحه پیدا نشد", status_code=404)

    def test_403_page_renders_custom_template(self):
        from django.core.exceptions import PermissionDenied
        from django.test import RequestFactory

        from config.views import custom_403

        factory = RequestFactory()
        request = factory.get("/")
        response = custom_403(request, exception=PermissionDenied())
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "دسترسی غیرمجاز", status_code=403)