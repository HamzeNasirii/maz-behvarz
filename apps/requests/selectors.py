from django.db.models import Q

from .choices import RequestStatus
from .models import Request


def requests_for_user(user):
    """Self-service — مالکیت مستقیم، بدون نیاز به Authorization Engine."""
    return Request.objects.filter(requester=user).select_related("scope")


def requests_for_management(user):
    """
    مرحله‌ی اول زنجیره‌ی امنیتی: Authorization Scope. هر تابع دیگری که
    فیلتر/جستجو اضافه می‌کند، باید حتماً روی خروجی همین تابع اعمال شود
    (طبق بخش ۲۵/۲۶ سند)، نه برعکس.
    """
    from apps.authorization.services import Authorization

    return Authorization.scope_queryset(user, Request.objects.select_related("requester", "scope"))


def filter_requests(queryset, *, status=None, request_type=None, date_from=None, date_to=None, search=None):
    """
    این تابع هیچ Scope اعمال نمی‌کند — باید همیشه روی یک QuerySet که
    قبلاً از requests_for_user()/requests_for_management() آمده صدا
    زده شود.
    """
    if status:
        queryset = queryset.filter(status=status)
    if request_type:
        queryset = queryset.filter(request_type=request_type)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))
    return queryset


ALLOWED_SORT_FIELDS = {"-created_at", "created_at", "status", "-status", "title", "-title"}


def sort_requests(queryset, sort_key):
    if sort_key not in ALLOWED_SORT_FIELDS:
        sort_key = "-created_at"
    return queryset.order_by(sort_key)


def pending_requests_for_management(user):
    queryset = requests_for_management(user).filter(
        status__in=[RequestStatus.SUBMITTED, RequestStatus.UNDER_REVIEW, RequestStatus.RESUBMITTED]
    )
    return queryset


def recently_returned_queue(user):
    return requests_for_management(user).filter(status=RequestStatus.RETURNED).order_by("-updated_at")[:20]


def recently_rejected_queue(user):
    return requests_for_management(user).filter(status=RequestStatus.REJECTED).order_by("-updated_at")[:20]


def recently_completed_queue(user):
    return requests_for_management(user).filter(status=RequestStatus.COMPLETED).order_by("-completed_at")[:20]


def request_history(request_obj):
    return request_obj.history.select_related("changed_by").all()