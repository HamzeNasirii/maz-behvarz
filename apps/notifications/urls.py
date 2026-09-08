from django.urls import path

from . import views

app_name = "notifications_portal"

urlpatterns = [
    path("portal/notifications/", views.notification_list_view, name="list"),
    path("portal/notifications/<int:pk>/", views.notification_detail_view, name="detail"),
    path("portal/notifications/<int:pk>/read/", views.mark_read_view, name="mark_read"),
    path("portal/notifications/mark-all-read/", views.mark_all_read_view, name="mark_all_read"),
]