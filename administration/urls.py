from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="adm_dashboard"),
    path("signin/", views.signin, name="adm_signin"),
    path("logout/", views.signout, name="adm_logout"),

    # Missions
    path("missions/", views.missions, name="adm_missions"),
    path("missions/create/", views.mission_create, name="adm_mission_create"),
    path("missions/<str:name>/edit/", views.mission_edit, name="adm_mission_edit"),
    path("missions/<str:name>/delete/", views.mission_delete, name="adm_mission_delete"),
    path("missions/<str:name>/assign/", views.mission_assign_all, name="adm_mission_assign"),

    # Products
    path("products/", views.products, name="adm_products"),
    path("products/create/", views.product_create, name="adm_product_create"),
    path("products/<str:name>/edit/", views.product_edit, name="adm_product_edit"),
    path("products/<str:name>/delete/", views.product_delete, name="adm_product_delete"),

    # Users
    path("users/", views.users, name="adm_users"),
]
