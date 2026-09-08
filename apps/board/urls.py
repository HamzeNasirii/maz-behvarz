from django.urls import path

from . import views

app_name = "board_mgmt"

urlpatterns = [
    path("management/board/", views.management_list_view, name="list"),
    path("management/board/create/", views.management_create_view, name="create"),
    path("management/board/<int:pk>/", views.management_detail_view, name="detail"),
    path("management/board/<int:pk>/activate/", views.activate_view, name="activate"),
    path("management/board/<int:pk>/suspend/", views.suspend_view, name="suspend"),
    path("management/board/<int:pk>/end/", views.end_view, name="end"),
    path("management/board/user-search/", views.user_search_suggestions_view, name="user_search"),
    path("management/board/<int:pk>/archive/", views.archive_view, name="archive"),
    path("management/board/<int:pk>/members/add/", views.member_add_view, name="member_add"),
    path("management/board/members/<int:membership_pk>/remove/", views.member_remove_view, name="member_remove"),
]