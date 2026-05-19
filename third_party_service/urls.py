# api/urls.py
from django.urls import path
from django.views.generic import TemplateView

from .views import (
    current_weather,
    daily_weather,
    get_stations_for_city,
    login_and_generate_key,
    register_and_get_key,
)

app_name = "third_party_service"
urlpatterns = [
    path("stations/", get_stations_for_city),
    path("weather/current/", current_weather),
    path("weather/daily/", daily_weather),
    path("register/", register_and_get_key, name="register_and_get_key"),
    path("login/", login_and_generate_key, name="login_and_generate_key"),
    path(
        "api/docs/",
        TemplateView.as_view(template_name="api_docs.html"),
        name="api-docs",
    ),
]
