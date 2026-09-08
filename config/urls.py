"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.authorization.admin_dashboard import pending_requests_view
from apps.public_content.sitemaps import (
    AnnouncementSitemap,
    EventSitemap,
    NewsSitemap,
    RegulationSitemap,
    StaticViewSitemap,
)
from apps.public_content.views import robots_txt_view

from . import views
from apps.public_content.feeds import LatestNewsFeed
sitemaps = {
    "news": NewsSitemap,
    "announcements": AnnouncementSitemap,
    "events": EventSitemap,
    "regulations": RegulationSitemap,
    "static": StaticViewSitemap,
}

urlpatterns = [
    path("admin/pending-requests/", pending_requests_view, name="pending_requests"),
    path("admin/reports/", include("apps.reports.urls")),
    path("admin/", admin.site.urls),
    path("health/", views.health_check_view, name="health_check"),
    path("api/organization/", include("apps.organization.urls")),
    path("api/v1/", include("apps.api.urls")),

    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("news/feed/", LatestNewsFeed(), name="news_feed"),
    path("robots.txt", robots_txt_view, name="robots_txt"),
    path("", include("apps.accounts.urls")),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            success_url="/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url="/password-reset-complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    path("", include("apps.members.urls")),
    path("", include("apps.members.fee_urls")),
    path("", include("apps.employment.urls")),
    path("", include("apps.authorization.reference_urls")),
    path("", include("apps.authorization.urls")),
    path("", include("apps.forums.urls")),
    path("", include("apps.committees.urls")),
    path("", include("apps.board.urls")),
    path("", include("apps.documents.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.requests.urls")),
    path("", include("apps.requests.management_urls")),
    path("", include("apps.authorization.pending_urls")),
    path("", include("apps.organization.management_urls")),
    path("", include("apps.public_content.management_urls")),
    path("", include("apps.public_content.urls")),
    path("", include("apps.website.urls")),
]

handler400 = "config.views.custom_400"
handler403 = "config.views.custom_403"
handler404 = "config.views.custom_404"
handler500 = "config.views.custom_500"
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)