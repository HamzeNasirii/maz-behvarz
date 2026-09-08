from django.urls import path

from . import views

app_name = "committees_mgmt"

urlpatterns = [
    path("management/committees/", views.management_list_view, name="list"),
    path("management/committees/create/", views.management_create_view, name="create"),
    path("management/committees/<int:pk>/", views.management_detail_view, name="detail"),
    path("management/committees/<int:pk>/activate/", views.activate_view, name="activate"),
    path("management/committees/<int:pk>/suspend/", views.suspend_view, name="suspend"),
    path("management/committees/<int:pk>/end/", views.end_view, name="end"),
    path("management/committees/<int:pk>/archive/", views.archive_view, name="archive"),
    path("management/committees/<int:pk>/members/add/", views.member_add_view, name="member_add"),
    path(
        "management/committees/members/<int:membership_pk>/remove/",
        views.member_remove_view, name="member_remove",
    ),
]