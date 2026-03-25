from .settings import *  # noqa: F403

DEBUG = False

SECRET_KEY = "test-secret-key"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test.sqlite3",  # noqa: F405
    }
}

MEDIA_ROOT = BASE_DIR / "test_media"  # noqa: F405
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = []

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
