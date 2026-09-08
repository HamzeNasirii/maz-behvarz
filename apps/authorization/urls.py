from django.urls import path

from . import views

app_name = "roles"

urlpatterns = [
    path("portal/roles/", views.portal_role_history_view, name="portal_roles"),
    path("management/roles/", views.management_list_view, name="management_list"),
    path("management/roles/<int:pk>/", views.management_detail_view, name="management_detail"),
    path("management/roles/<int:pk>/submit/", views.submit_view, name="submit"),
    path("management/roles/<int:pk>/approve/", views.approve_view, name="approve"),
    path("management/roles/<int:pk>/reject/", views.reject_view, name="reject"),
    path("management/roles/<int:pk>/suspend/", views.suspend_view, name="suspend"),
    path("management/roles/<int:pk>/reactivate/", views.reactivate_view, name="reactivate"),
    path("management/roles/<int:pk>/end/", views.end_view, name="end"),
    path("management/roles/<int:pk>/revoke/", views.revoke_view, name="revoke"),
    path("management/roles/<int:pk>/cancel/", views.cancel_view, name="cancel"),
]