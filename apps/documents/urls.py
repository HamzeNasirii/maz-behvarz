from django.urls import path

from . import views

app_name = "documents_mgmt"

urlpatterns = [
    path("management/documents/", views.management_list_view, name="list"),
    path("management/documents/upload/", views.upload_view, name="upload"),
    path("management/documents/<int:pk>/", views.management_detail_view, name="detail"),
    path("management/documents/<int:pk>/submit-review/", views.submit_review_view, name="submit_review"),
    path("management/documents/<int:pk>/approve/", views.approve_view, name="approve"),
    path("management/documents/<int:pk>/reject/", views.reject_view, name="reject"),
    path("management/documents/<int:pk>/publish/", views.publish_view, name="publish"),
    path("management/documents/<int:pk>/archive/", views.archive_view, name="archive"),
    path("management/documents/<int:pk>/download/", views.download_view, name="download"),
]