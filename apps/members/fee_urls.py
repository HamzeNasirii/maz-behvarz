from django.urls import path

from . import fee_views as views

app_name = "members_fees"

urlpatterns = [
    path("management/members/fees/", views.fee_list_view, name="list"),
    path("management/members/<int:member_pk>/fees/create/", views.fee_create_view, name="create"),
    path("management/members/fees/<int:pk>/pay/", views.fee_mark_paid_view, name="mark_paid"),
    path("management/members/fees/<int:pk>/delete/", views.fee_delete_view, name="delete"),
    path("management/members/fees/<int:pk>/edit-request/", views.fee_edit_request_view, name="edit_request"),
    path("management/members/fees/<int:pk>/delete-request/", views.fee_delete_request_view, name="delete_request"),
    path("management/members/fees/changes/", views.fee_change_list_view, name="change_list"),
    path("management/members/fees/changes/<int:pk>/approve/", views.fee_change_approve_view, name="change_approve"),
    path("management/members/fees/changes/<int:pk>/reject/", views.fee_change_reject_view, name="change_reject"),
    path("management/members/fees/report/", views.treasurer_financial_report_view, name="financial_report"),

    path("management/members/fees/changes/<int:pk>/cancel/", views.fee_change_cancel_view, name="change_cancel"),

]