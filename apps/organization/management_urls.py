from django.urls import path

from . import management_views as views

app_name = "org_mgmt"

urlpatterns = [
    path("management/organization/search-suggestions/", views.org_search_suggestions_view, name="search_suggestions"),
    path("management/organization/", views.org_tree_view, name="tree"),
    path("management/organization/<str:level>/<int:pk>/", views.org_detail_view, name="detail"),
    path("management/organization/<str:level>/create/", views.org_create_view, name="create"),
    path("management/organization/<str:level>/<int:pk>/edit/", views.org_edit_view, name="edit"),
    path("management/organization/<str:level>/<int:pk>/toggle/", views.org_toggle_active_view, name="toggle"),
]