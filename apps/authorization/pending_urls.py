from django.urls import path

from . import pending_views as views

app_name = "pending_mgmt"

urlpatterns = [
    path("management/pending/applications/", views.pending_applications_view, name="applications"),
    path("management/pending/members/", views.pending_members_view, name="members"),
    path("management/pending/employment/", views.pending_employment_view, name="employment"),
    path("management/pending/roles/", views.pending_roles_view, name="roles"),
]