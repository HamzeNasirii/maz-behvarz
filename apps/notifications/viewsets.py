from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer
from .services import mark_as_read


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    هر کاربر فقط اطلاعیه‌های خودش را می‌بیند — بدون نیاز به
    Authorization Engine، چون مالکیت مستقیماً در کوئری تضمین شده.
    """

    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.for_user(self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        mark_as_read(notification=notification)
        return Response(NotificationSerializer(notification).data)