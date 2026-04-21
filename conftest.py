import os

def pytest_configure():
    # CANVIA AIXÒ pel mòdul real del teu settings de test
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")