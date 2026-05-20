from .settings_test import *  # noqa: F403,F401

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "coverage_test.sqlite3",  # noqa: F405
    }
}

CONN_MAX_AGE = 0