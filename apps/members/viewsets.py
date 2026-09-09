from rest_framework import viewsets

from apps.authorization.services import Authorization

from .models import Member
from .serializers import MemberSerializer


class MemberViewSet(viewsets.ReadOnlyModelViewSet):
    """
    فقط Read — ویرایش عضو از طریق Workflow تأیید (گام ۱۱) انجام
    می‌شود، نه مستقیم از API.

    هر کاربر همیشه پروفایل خودش را می‌بیند (صرف‌نظر از RBAC/Scope)،
    به‌علاوه‌ی هر عضوی که در محدوده‌ی دسترسی او (از طریق RoleAssignment)
    قرار دارد.
    """

    serializer_class = MemberSerializer

    def get_queryset(self):
        base = Member.objects.select_related("user").prefetch_related("membership_periods")
        own_ids = base.filter(user=self.request.user).values_list("pk", flat=True)
        scoped_ids = Authorization.scope_queryset(self.request.user, base).values_list("pk", flat=True)
        combined_ids = set(own_ids) | set(scoped_ids)
        return base.filter(pk__in=combined_ids)