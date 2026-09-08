def is_approved_member_flag(request):
    """
    آیا کاربر لاگین‌شده از قبل عضو تأییدشده است؟ برای مخفی‌کردن لینک
    «درخواست عضویت» از افرادی که دیگر نیازی به درخواست مجدد ندارند.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    is_approved = hasattr(user, "member_profile") and user.member_profile.approval_status == "approved"
    return {"is_approved_member": is_approved}

def static_version(request):
    from django.conf import settings
    return {"STATIC_VERSION": settings.STATIC_VERSION}