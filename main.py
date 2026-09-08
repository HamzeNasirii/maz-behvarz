import os
import subprocess
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

port = os.environ.get("PORT", "8000")

subprocess.run([
    "gunicorn",
    "config.wsgi:application",
    "--bind", f"0.0.0.0:{port}",
    "--workers", "3",
])