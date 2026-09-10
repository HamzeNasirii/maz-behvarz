import os
import subprocess
import sys
from pathlib import Path

print("=== MAIN.PY STARTED ===", flush=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
port = os.environ.get("PORT", "8000")


def run_required(label, command):
    """Run a deployment step and never start the web server after a failure."""
    print(f"=== {label} ===", flush=True)
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"=== {label} FAILED: EXIT CODE {exc.returncode} ===", flush=True)
        raise SystemExit(exc.returncode)


run_required(
    "RUNNING MIGRATE",
    [sys.executable, "manage.py", "migrate", "--noinput"],
)

run_required(
    "RUNNING COLLECTSTATIC",
    [sys.executable, "manage.py", "collectstatic", "--noinput", "--clear"],
)

# Verify the result that WhiteNoise / the hosting static route must serve.
from django.conf import settings  # imported only after DJANGO_SETTINGS_MODULE is set

static_root = Path(settings.STATIC_ROOT)
print(f"=== STATIC_ROOT: {static_root} ===", flush=True)

if not static_root.is_dir():
    print("=== STATIC CHECK FAILED: STATIC_ROOT DOES NOT EXIST ===", flush=True)
    raise SystemExit(1)

navigation_files = list((static_root / "js").glob("navigation*.js"))
if not navigation_files:
    print("=== STATIC CHECK FAILED: navigation.js WAS NOT COLLECTED ===", flush=True)
    raise SystemExit(1)

file_count = sum(1 for path in static_root.rglob("*") if path.is_file())
print(f"=== STATIC CHECK OK: {file_count} FILES COLLECTED ===", flush=True)
print(
    "=== NAVIGATION FILES: "
    + ", ".join(path.name for path in navigation_files[:10])
    + " ===",
    flush=True,
)

print("=== STARTING GUNICORN ===", flush=True)
subprocess.run(
    [
        "gunicorn",
        "config.wsgi:application",
        "--bind",
        f"0.0.0.0:{port}",
        "--workers",
        "3",
        "--access-logfile",
        "-",
        "--error-logfile",
        "-",
    ],
    check=True,
)
