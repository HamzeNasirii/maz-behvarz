from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Notification
from .services import mark_as_read


@login_required
def notification_list_view(request):
    """مالکیت از طریق request.user تضمین شده — نیازی به Authorization Engine نیست."""
    notifications = Notification.objects.for_user(request.user)
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
def notification_detail_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    if notification.recipient_id != request.user.id:
        raise PermissionDenied("این اطلاعیه متعلق به شما نیست.")

    if not notification.is_read:
        mark_as_read(notification=notification)

    return render(request, "notifications/detail.html", {"notification": notification})

@login_required
def mark_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    if notification.recipient_id != request.user.id:
        raise PermissionDenied("این اطلاعیه متعلق به شما نیست.")
    mark_as_read(notification=notification)
    return redirect("notifications_portal:list")


@login_required
def mark_all_read_view(request):
    Notification.objects.for_user(request.user).unread().update(is_read=True, read_at=timezone.now())
    return redirect("notifications_portal:list")