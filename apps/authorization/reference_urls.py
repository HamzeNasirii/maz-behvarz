from django.urls import path

from . import reference_views as views

app_name = "auth_ref"

urlpatterns = [
    path("management/roles-catalog/", views.role_list_view, name="role_list"),
    path("management/roles-catalog/create/", views.role_create_view, name="role_create"),
    path("management/roles-catalog/<int:pk>/edit/", views.role_edit_view, name="role_edit"),
    path("management/roles-catalog/<int:pk>/toggle/", views.role_toggle_view, name="role_toggle"),

    path("management/permissions/", views.permission_list_view, name="permission_list"),
    path("management/permissions/create/", views.permission_create_view, name="permission_create"),
    path("management/permissions/<int:pk>/edit/", views.permission_edit_view, name="permission_edit"),

    path("management/scopes/", views.scope_list_view, name="scope_list"),
    path("management/scopes/create/", views.scope_create_view, name="scope_create"),
]