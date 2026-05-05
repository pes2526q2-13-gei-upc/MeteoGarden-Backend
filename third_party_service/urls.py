# api/urls.py
from django.urls import path
from .views import current_weather, daily_weather

urlpatterns = [
    path("weather/current/", current_weather),
    path("weather/daily/",   daily_weather),
]