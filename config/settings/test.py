from .base import *

DEBUG = False

ALLOWED_HOSTS = ["testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "OPTIONS": {
            "timeout": 20,  # ثانیه — جلوگیری از خطای گذرا "database is locked"
        },
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
