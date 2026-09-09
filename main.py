import os
import subprocess
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

port = os.environ.get("PORT", "8000")

# اجرای خودکار Migration و Collectstatic در هر بار استارت کانتینر —
# چون فایل‌سیستم کانتینر موقت است و هر بار Restart/Deploy، از صفر
# ساخته می‌شود؛ اجرای دستی این دستورها در Terminal دائمی نیست.
subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], check=True)
subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"], check=True)

subprocess.run([
    "gunicorn",
    "config.wsgi:application",
    "--bind", f"0.0.0.0:{port}",
    "--workers", "3",
])