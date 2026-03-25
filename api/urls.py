"""
URL configuration for api.
"""

# from django.contrib import admin
from django.urls import path

from .views import (
    collect_plant,
    current_weather,
    edit_profile,
    garden_plants,
    get_profile,
    get_stations,
    getUserAlbum,
    health,
    identifyPlant,
    importPlant,
    login,
    plant_seed,
    plant_status,
    register,
    user_gardens,
    user_products,
    user_seeds,
    water_plant,
)

urlpatterns = [
    path("health/", health),
    path("register/", register),
    path("login/", login),
    path("get_profile/", get_profile),
    path("edit_profile/", edit_profile),
    path("users/<str:username>/gardens/", user_gardens, name="user_gardens"),
    path(
        "users/<str:username>/gardens/<str:garden_name>/plants/",
        garden_plants,
        name="garden-plants",
    ),
    path(
        "users/<str:username>/gardens/<str:garden_name>/pots/<int:pot_number>/plant/",
        plant_status,
        name="plant_status",
    ),
    path("weather/current/", current_weather),
    path("stations/", get_stations),
    path("plants/info/", importPlant),
    path("plants/identify", identifyPlant, name="identifyPlant"),
    path("album/", getUserAlbum),
    path(
        "users/<str:username>/gardens/<str:garden_name>/pots/<int:pot_number>/water/",
        water_plant,
        name="water_plant",
    ),
    path(
        "users/<str:username>/seeds/",
        user_seeds,
        name="user_seeds",
    ),
    path(
        "users/<str:username>/products/",
        user_products,
        name="user_products",
    ),
    path(
        "users/<str:username>/gardens/<str:garden_name>/pots/<int:pot_number>/planting/",
        plant_seed,
        name="plant_seed",
    ),
    path(
        "users/<str:username>/gardens/<str:garden_name>/pots/<int:pot_number>/collect/",
        collect_plant,
        name="collect_plant",
    ),
]
