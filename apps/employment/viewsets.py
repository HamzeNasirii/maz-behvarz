from rest_framework import viewsets

from apps.authorization.services import Authorization

from .models import EmploymentAssignment
from .serializers import EmploymentAssignmentSerializer


class EmploymentAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    هر کاربر همیشه تخصیص‌های محل خدمت خودش را می‌بیند، به‌علاوه‌ی هر
    تخصیصی که در محدوده‌ی دسترسی او (RoleAssignment) قرار دارد.
    """

    serializer_class = EmploymentAssignmentSerializer

    def get_queryset(self):
        base = EmploymentAssignment.objects.select_related(
            "user", "health_house", "health_house__center"
        )
        own = base.filter(user=self.request.user)
        scoped = Authorization.scope_queryset(self.request.user, base)
        return (own | scoped).distinct()