from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """
    اگر کاربر لاگین‌شده هنوز رمز پیش‌فرض (شماره ملی) را عوض نکرده
    باشد، به‌جز صفحه‌ی خودِ تغییر رمز و خروج، به هر مسیر دیگری برود،
    مستقیم به صفحه‌ی تغییر رمز هدایت می‌شود.
    """

    EXEMPT_PATHS = {
        "members_portal:forced_password_change",
        "logout",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and getattr(user, "must_change_password", False):
            exempt_urls = {reverse(name) for name in self.EXEMPT_PATHS}
            if request.path not in exempt_urls and not request.path.startswith("/static/") and not request.path.startswith("/media/"):
                return redirect("members_portal:forced_password_change")
        return self.get_response(request)