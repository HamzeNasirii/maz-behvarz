from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.website"

    def ready(self):
        from apps.authorization.registry import register_health_house_resolver, register_queryset_scope_resolver

        from .models import MembershipApplication
        from .resolvers import membership_application_health_houses, scope_membership_application_queryset

        register_health_house_resolver(MembershipApplication, membership_application_health_houses)
        register_queryset_scope_resolver(MembershipApplication, scope_membership_application_queryset)

        self._run_startup_tasks_once()

    def _run_startup_tasks_once(self):
        """
        اجرای Migration و Collectstatic دقیقاً یک‌بار، صرف‌نظر از این‌که
        Gunicorn چند Worker همزمان بالا بیاورد — چون این پلتفرم (RunFlare)
        اجازه‌ی تعریف یک دستور Start سفارشی (مثل main.py مستقل) را قبل
        از Gunicorn نمی‌دهد، این کار باید از داخل خود اپلیکیشن، در اولین
        بارگذاری، انجام شود. یک فایل Marker روی دیسک از اجرای تکراری
        توسط سایر Workerها جلوگیری می‌کند.
        """
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        marker_path = Path(tempfile.gettempdir()) / "startup_tasks_done"

        if marker_path.exists():
            return

        try:
            marker_path.touch(exist_ok=False)
        except FileExistsError:
            return

        print("=== RUNNING STARTUP TASKS (migrate + collectstatic) ===", flush=True)

        result = subprocess.run(
            [sys.executable, "manage.py", "migrate", "--noinput"]
        )
        print(f"=== MIGRATE EXIT CODE: {result.returncode} ===", flush=True)

        result = subprocess.run(
            [sys.executable, "manage.py", "collectstatic", "--noinput"]
        )
        print(f"=== COLLECTSTATIC EXIT CODE: {result.returncode} ===", flush=True)
        self._ensure_superuser()
        print("=== STARTUP TASKS DONE ===", flush=True)

    def _ensure_superuser(self):
        """
        ساخت خودکار Superuser در اولین Deploy — فقط اگر از قبل هیچ
        Superuser‌ای در دیتابیس وجود نداشته باشد (Idempotent، بی‌خطر
        برای Deployهای بعدی).
        """
        from django.contrib.auth import get_user_model
        from django.conf import settings

        User = get_user_model()

        if User.objects.filter(is_superuser=True).exists():
            print("=== SUPERUSER ALREADY EXISTS — SKIPPING ===", flush=True)
            return

        username = getattr(settings, "INITIAL_SUPERUSER_USERNAME", None)
        password = getattr(settings, "INITIAL_SUPERUSER_PASSWORD", None)

        if not username or not password:
            print("=== NO INITIAL_SUPERUSER_USERNAME/PASSWORD SET — SKIPPING SUPERUSER CREATION ===", flush=True)
            return

        User.objects.create_superuser(username=username, password=password)
        print(f"=== SUPERUSER '{username}' CREATED ===", flush=True)
