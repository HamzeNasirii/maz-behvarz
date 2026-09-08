from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from apps.employment.viewsets import EmploymentAssignmentViewSet
from apps.members.viewsets import MemberViewSet
from apps.notifications.viewsets import NotificationViewSet
from apps.website.viewsets import MembershipApplicationViewSet

router = DefaultRouter()
router.register("members", MemberViewSet, basename="member")
router.register("employment-assignments", EmploymentAssignmentViewSet, basename="employmentassignment")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("membership-applications", MembershipApplicationViewSet, basename="membershipapplication")

urlpatterns = [
    path("token/", obtain_auth_token, name="api_token_auth"),
    path("", include(router.urls)),
]