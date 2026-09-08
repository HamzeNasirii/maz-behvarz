from django import template

from apps.website.utils import gregorian_to_jalali

register = template.Library()


@register.filter
def jalali(value):
    """تبدیل هر تاریخ میلادی به رشته‌ی شمسی — برای استفاده در همه‌ی Templateها."""
    if not value:
        return ""
    try:
        jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
        return f"{jy}/{jm:02d}/{jd:02d}"
    except (AttributeError, ValueError):
        return value

from apps.website.utils import full_jalali_date


@register.filter
def full_jalali(value):
    if not value:
        return ""
    try:
        return full_jalali_date(value)
    except (AttributeError, ValueError):
        return value


@register.filter
def comma(value):
    """نمایش عدد با جداکننده‌ی هزارگان — برای مبالغ مالی."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value