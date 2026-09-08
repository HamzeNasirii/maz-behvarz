from django.urls import path

from . import views

app_name = "forums"

urlpatterns = [
    path("forums/", views.forum_list_view, name="list"),
    path("forums/<int:pk>/", views.forum_detail_view, name="detail"),
    path("forums/<int:forum_pk>/posts/create/", views.post_create_view, name="post_create"),
    path("forums/posts/<int:pk>/", views.post_detail_view, name="post_detail"),
    path("forums/posts/<int:pk>/delete/", views.post_delete_view, name="post_delete"),
    path("forums/comments/<int:pk>/delete/", views.comment_delete_view, name="comment_delete"),
    path("forums/react/<str:target_type>/<int:pk>/", views.reaction_toggle_view, name="react"),
    path("management/forums/coverage/", views.forum_coverage_view, name="coverage"),
    path("management/forums/quick-create/<str:level>/<int:pk>/", views.forum_quick_create_view, name="quick_create"),
    path("management/forums/<int:pk>/toggle/", views.forum_toggle_active_view, name="toggle_active"),

    path("management/forums/", views.forum_management_list_view, name="management_list"),
    path("management/forums/create/", views.forum_management_create_view, name="management_create"),
]