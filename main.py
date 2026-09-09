import os
import subprocess
import sys

print("=== MAIN.PY STARTED ===", flush=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

port = os.environ.get("PORT", "8000")

print("=== RUNNING MIGRATE ===", flush=True)
result = subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"])
print(f"=== MIGRATE EXIT CODE: {result.returncode} ===", flush=True)

print("=== RUNNING COLLECTSTATIC ===", flush=True)
result = subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"])
print(f"=== COLLECTSTATIC EXIT CODE: {result.returncode} ===", flush=True)

print("=== STARTING GUNICORN ===", flush=True)
subprocess.run([
    "gunicorn",
    "config.wsgi:application",
    "--bind", f"0.0.0.0:{port}",
    "--workers", "3",
])