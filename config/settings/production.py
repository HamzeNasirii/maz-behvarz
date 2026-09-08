from decouple import config

from .base import *

DEBUG = False

ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="").split(",")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DATABASE_NAME"),
        "USER": config("DATABASE_USER"),
        "PASSWORD": config("DATABASE_PASSWORD"),
        "HOST": config("DATABASE_HOST", default="localhost"),
        "PORT": config("DATABASE_PORT", default="5432"),
    }
}

CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="").split(",")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# --- WhiteNoise فقط در Production فعال است ---
MIDDLEWARE = MIDDLEWARE.copy()
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# TODO: SMTP واقعی در فاز بعدی که Notification Engine کامل می‌شود تنظیم شود.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"