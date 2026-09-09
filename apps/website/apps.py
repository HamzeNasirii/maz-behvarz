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
        import os
        import subprocess
        import sys

        marker_path = "/tmp/startup_tasks_done"
        if os.path.exists(marker_path):
            return

        try:
            with open(marker_path, "x"):
                pass
        except FileExistsError:
            return

        print("=== RUNNING STARTUP TASKS (migrate + collectstatic) ===", flush=True)

        result = subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"])
        print(f"=== MIGRATE EXIT CODE: {result.returncode} ===", flush=True)

        result = subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"])
        print(f"=== COLLECTSTATIC EXIT CODE: {result.returncode} ===", flush=True)

        print("=== STARTUP TASKS DONE ===", flush=True)