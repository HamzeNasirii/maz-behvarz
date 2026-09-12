from decouple import config

from .base import *

DEBUG = False


def _csv_setting(name, default=""):
    """Read a comma-separated env var and drop blank/whitespace-only items."""
    return [item.strip() for item in config(name, default=default).split(",") if item.strip()]


ALLOWED_HOSTS = _csv_setting(
    "DJANGO_ALLOWED_HOSTS",
    default="maz-behvarz.ir,www.maz-behvarz.ir",
)

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

CSRF_TRUSTED_ORIGINS = _csv_setting(
    "CSRF_TRUSTED_ORIGINS",
    default="https://maz-behvarz.ir,https://www.maz-behvarz.ir",
)

# HTTPS is terminated by the hosting platform / Nginx before the request reaches
# Gunicorn. Trust the standard proxy header so Django can correctly identify the
# original request scheme when the proxy sends X-Forwarded-Proto: https.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Do not perform a second HTTP -> HTTPS redirect inside Django by default.
# The hosting platform or the bundled Nginx config already owns that redirect.
# This avoids ERR_TOO_MANY_REDIRECTS when TLS is terminated at a reverse proxy.
# Set DJANGO_SECURE_SSL_REDIRECT=True only if your deployment explicitly needs
# Django itself to enforce the redirect and your proxy forwards X-Forwarded-Proto.
SECURE_SSL_REDIRECT = config(
    "DJANGO_SECURE_SSL_REDIRECT",
    default=False,
    cast=bool,
)

SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# --- WhiteNoise فقط در Production فعال است ---
MIDDLEWARE = MIDDLEWARE.copy()
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# Static assets are collected into BASE_DIR/static.  This matches the
# original deployment layout used by the hosted application and the bundled
# Nginx configuration.  Override only when your hosting panel is explicitly
# configured for a different directory.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / config("DJANGO_STATIC_ROOT_DIR", default="static")

# Be explicit so WhiteNoise always recognizes /static/... requests behind a
# reverse proxy / PaaS router.
WHITENOISE_STATIC_PREFIX = "/static/"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# TODO: SMTP واقعی در فاز بعدی که Notification Engine کامل می‌شود تنظیم شود.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}

INITIAL_SUPERUSER_USERNAME = config("INITIAL_SUPERUSER_USERNAME", default="")
INITIAL_SUPERUSER_PASSWORD = config("INITIAL_SUPERUSER_PASSWORD", default="")