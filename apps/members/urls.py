from django.urls import path

from . import views

app_name = "members_portal"

urlpatterns = [
    path("portal/documents/", views.member_documents_view, name="documents"),
    path("portal/", views.portal_dashboard_view, name="dashboard"),
    path("portal/employment-history/", views.portal_employment_history_view, name="employment_history"),
    path("portal/profile/", views.profile_view, name="profile"),
    path("portal/profile/edit/", views.profile_edit_view, name="profile_edit"),
    path("portal/change-password/", views.forced_password_change_view, name="forced_password_change"),
    path("management/members/", views.member_list_view, name="member_list"),
    path("management/members/<int:pk>/", views.member_detail_view, name="member_detail"),
    path("portal/membership/", views.membership_status_view, name="membership_status"),
    path("portal/membership/apply/", views.membership_apply_view, name="membership_apply"),
    path("management/membership/", views.membership_management_list_view, name="membership_management_list"),
    path("management/membership/<int:pk>/", views.membership_management_detail_view,
         name="membership_management_detail"),
    path("portal/bale-link/", views.bale_link_start_view, name="bale_link"),
    path("portal/fees/<int:fee_pk>/pay-bale/", views.bale_fee_payment_view, name="bale_fee_payment"),
    path("portal/my-fees/", views.my_fees_view, name="my_fees"),
    path("management/members/<int:pk>/documents/<str:document_key>/approve/", views.member_document_approve_view,
         name="document_approve"),
    path("management/members/<int:pk>/documents/<str:document_key>/reject/", views.member_document_reject_view,
         name="document_reject"),
    path("management/members/hub/", views.members_hub_view, name="hub"),
    path("management/membership/<int:pk>/review/", views.membership_review_view, name="membership_review"),
    path("management/membership/<int:pk>/approve/", views.membership_approve_view, name="membership_approve"),
    path("management/membership/<int:pk>/reject/", views.membership_reject_view, name="membership_reject"),
    path("management/membership/<int:pk>/suspend/", views.membership_suspend_view, name="membership_suspend"),
    path("management/membership/<int:pk>/reinstate/", views.membership_reinstate_view, name="membership_reinstate"),
    path("management/membership/<int:pk>/expire/", views.membership_expire_view, name="membership_expire"),
    path("management/membership/<int:pk>/cancel/", views.membership_cancel_view, name="membership_cancel"),
    path("management/members/<int:member_pk>/propose-removal/", views.removal_proposal_create_view,
         name="propose_removal"),
    path("management/members/removal-proposals/", views.removal_proposal_list_view, name="removal_proposals"),
    path("management/members/removal-proposals/<int:pk>/approve/", views.removal_proposal_approve_view,
         name="removal_approve"),
    path("management/members/removal-proposals/<int:pk>/reject/", views.removal_proposal_reject_view,
         name="removal_reject"),
    path("management/members/search-suggestions/", views.member_search_suggestions_view,
         name="member_search_suggestions"),

]
