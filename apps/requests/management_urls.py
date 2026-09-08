from django.urls import path

from . import views

app_name = "requests_mgmt"

urlpatterns = [
    path("management/requests/queue/", views.management_queue_view, name="queue"),
    path("management/requests/", views.management_list_view, name="list"),
    path("management/requests/<int:pk>/", views.management_detail_view, name="detail"),
    path("management/requests/<int:pk>/review/", views.review_view, name="review"),
    path("management/requests/<int:pk>/approve/", views.approve_view, name="approve"),
    path("management/requests/<int:pk>/reject/", views.reject_view, name="reject"),
    path("management/requests/<int:pk>/return/", views.return_view, name="return"),
    path("management/requests/<int:pk>/complete/", views.complete_view, name="complete"),
]