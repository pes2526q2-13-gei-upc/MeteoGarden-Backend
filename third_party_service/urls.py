# api/urls.py
from django.urls import path
from .views import current_weather, daily_weather, create_api_key

urlpatterns = [
    path("weather/current/", current_weather),
    path("weather/daily/",   daily_weather),
    path("apikey/", create_api_key, name="create-api-key"),
]