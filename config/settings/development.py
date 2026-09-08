from decouple import config

from .base import *

DEBUG = True

ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1"
).split(",")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# نکته: SQLite فقط برای راحتی توسعه محلی استفاده می‌شود.
# Production باید حتماً از PostgreSQL استفاده کند (production.py).
# برخی Constraintها (مثل CHECK constraint) در SQLite به همان دقت
# PostgreSQL اعمال نمی‌شوند؛ قبل از اتکا به آن‌ها در Production باید
# روی PostgreSQL دوباره صحت‌سنجی شوند.

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"