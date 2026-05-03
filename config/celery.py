import os

from celery import Celery

# Defineix el mòdul de configuració de Django per defecte
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("config")

# Llegeix la configuració de Celery des del settings.py amb el prefix CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Carrega les tasques (tasks.py) de totes les apps registrades a INSTALLED_APPS
app.autodiscover_tasks()
