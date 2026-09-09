from django.test import TestCase
from django.urls import reverse

from apps.public_content.models import PublicDocument


class SEOTests(TestCase):
    def test_robots_txt_accessible(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Disallow: /admin/", response.content)

    def test_sitemap_xml_accessible(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<urlset", response.content)

    def test_home_page_has_canonical_link(self):
        response = self.client.get(reverse("website:home"))
        self.assertContains(response, 'rel="canonical"')

    def test_home_page_has_meta_description(self):
        response = self.client.get(reverse("website:home"))
        self.assertContains(response, 'name="description"')


class SecurityTests(TestCase):
    def _make_file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile("secret.pdf", b"private content", content_type="application/pdf")

    def test_private_document_file_url_not_listed_publicly(self):
        private_doc = PublicDocument.objects.create(
            title="سند محرمانه", file=self._make_file(), is_public=False, is_published=True
        )
        response = self.client.get(reverse("public_content:document_list"))
        self.assertNotContains(response, "سند محرمانه")

    def test_csrf_protected_contact_form(self):
        """
        بررسی وجود CSRF Middleware — درخواست POST بدون توکن معتبر
        (از طریق کلاینت enforce_csrf_checks) باید رد شود.
        """
        from django.test import Client

        strict_client = Client(enforce_csrf_checks=True)
        response = strict_client.post(reverse("public_content:contact"), {
            "name": "تست", "email": "a@a.com", "subject": "س", "message": "پیام آزمایشی طولانی",
        })
        self.assertEqual(response.status_code, 403)

    def test_malformed_slug_returns_404_not_500(self):
        response = self.client.get("/news/<script>alert(1)</script>/")
        self.assertIn(response.status_code, [404, 400])


class URLCoverageTests(TestCase):
    """طبق STEP 51 سند: تمام URLهای Public باید تست شوند."""

    def test_all_public_urls_return_200(self):
        urls = [
            reverse("website:home"),
            reverse("website:about"),
            reverse("website:about_history"),
            reverse("website:about_mission"),
            reverse("website:about_objectives"),
            reverse("website:about_organizational_structure"),
            reverse("public_content:news_list"),
            reverse("public_content:announcement_list"),
            reverse("public_content:event_list"),
            reverse("public_content:board"),
            reverse("public_content:committees"),
            reverse("public_content:document_list"),
            reverse("public_content:regulation_list"),
            reverse("public_content:faq"),
            reverse("website:contact"),
            reverse("public_content:search"),
            reverse("website:privacy"),
            reverse("website:terms"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, f"{url} returned {response.status_code}")