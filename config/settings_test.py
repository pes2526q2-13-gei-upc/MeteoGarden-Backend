import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key")

from .settings import *  # noqa: F403, E402, F401

DEBUG = False

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "test-secret-key")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "meteogarden"),
        "USER": os.getenv("POSTGRES_USER", "meteogarden"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

MEDIA_ROOT = BASE_DIR / "test_media"

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = []

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

FIREBASE_ENABLED = False
