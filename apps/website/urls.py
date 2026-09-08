from django.urls import path

from . import views

app_name = "website"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("about/", views.about_view, name="about"),
    path("about/history/", views.about_history_view, name="about_history"),
    path("about/mission/", views.about_mission_view, name="about_mission"),
    path("about/objectives/", views.about_objectives_view, name="about_objectives"),
    path(
        "about/organizational-structure/",
        views.about_organizational_structure_view,
        name="about_organizational_structure",
    ),
    path("contact/", views.contact_view, name="contact"),
    path("privacy/", views.privacy_view, name="privacy"),
    path("terms/", views.terms_view, name="terms"),
    path("membership/apply/letter/", views.membership_letter_view, name="membership_letter"),
    path("membership/apply/", views.membership_application_view, name="membership_application"),
    path(
        "membership/apply/success/",
        views.membership_application_success_view,
        name="membership_application_success",
    ),
]