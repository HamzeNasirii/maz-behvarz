from django import template

register = template.Library()

_BADGE_MAP = {
    "draft": "inactive",
    "submitted": "pending",
    "under_review": "pending",
    "resubmitted": "pending",
    "returned": "pending",
    "approved": "approved",
    "completed": "approved",
    "rejected": "rejected",
    "cancelled": "rejected",
}


@register.filter
def request_status_badge(status):
    """کلاس badge-* مناسب برای هر وضعیت Request — طبق RequestStatus."""
    return _BADGE_MAP.get(status, "inactive")