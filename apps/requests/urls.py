from django.urls import path

from . import views

app_name = "requests_portal"

urlpatterns = [
    path("portal/requests/", views.portal_list_view, name="list"),
    path("portal/requests/create/", views.portal_create_view, name="create"),
    path("portal/requests/<int:pk>/", views.portal_detail_view, name="detail"),
    path("portal/requests/<int:pk>/submit/", views.portal_submit_view, name="submit"),
    path("portal/requests/<int:pk>/resubmit/", views.portal_resubmit_view, name="resubmit"),
    path("portal/requests/<int:pk>/attach-document/", views.portal_attach_document_view, name="attach_document"),
    path("portal/requests/<int:pk>/cancel/", views.portal_cancel_view, name="cancel"),
]