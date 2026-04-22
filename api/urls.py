"""
URL configuration for api.
"""

# from django.contrib import admin
from django.urls import path

from .views import (
    buy_item,
    collect_plant,
    current_weather,
    delete_plant,
    delete_profile,
    edit_profile,
    garden_plants,
    get_profile,
    get_shop,
    get_stations,
    getImages,
    getUserAlbum,
    getUserAvatar,
    google_register,
    google_verify,
    health,
    identifyPlant,
    importPlant,
    login,
    plant_seed,
    plant_status,
    register,
    saveAvatar,
    translate,
    use_product,
    user_gardens,
    user_products,
    user_seeds,
    validate_token,
    water_plant,
)

urlpatterns = [
    path("health/", health),
    path("register/", register),
    path("login/", login),
    path("get_profile/", get_profile),
    path("edit_profile/", edit_profile),
    path("delete_profile/", delete_profile),
    path("auth/google/verify", google_verify),
    path("auth/google/register", google_register),
    path("validate_token/", validate_token),
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
    path("users/<str:username>/album/", getUserAlbum),
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
    path("translate/", translate),
    path("shop/", get_shop, name="get_shop"),
    path("users/<str:username>/buy/", buy_item, name="buy_item"),
    path("use-product/", use_product),
    path("avatar/", getImages, name="avatar_images"),
    path("users/<str:username>/avatar", getUserAvatar, name="user_avatar"),
    path("users/<str:username>/save/avatar", saveAvatar, name="save_avatar"),
    path(
        "users/<str:username>/gardens/<str:garden_name>/pots/<int:pot_number>/delete/",
        delete_plant,
        name="delete_plant",
    ),
]
