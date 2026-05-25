from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from api.models import Mission, Product, UserMission

User = get_user_model()


def create_staff():
    return User.objects.create_user(
        username="admin",
        password="admin123",
        is_staff=True,
    )


def logged_client():
    create_staff()
    client = Client()
    client.login(username="admin", password="admin123")
    return client


def create_mission(name="Test Mission"):
    return Mission.objects.create(
        name=name,
        description="desc",
        action="PLANT",
        goal=1,
        rewardCoins=10,
    )


def create_product(name="Test Product"):
    return Product.objects.create(
        name=name,
        description="desc",
        effectType="growth",
        price=10,
        rarity="common",
        isInstant=True,
    )


def test_signin_page_loads(db):
    response = Client().get(reverse("adm_signin"))
    assert response.status_code == 200


def test_signin_valid_staff_redirects(db):
    create_staff()
    client = Client()

    response = client.post(
        reverse("adm_signin"),
        {
            "username": "admin",
            "password": "admin123",
        },
    )

    assert response.status_code == 302


def test_signin_invalid_credentials_shows_error(db):
    response = Client().post(
        reverse("adm_signin"),
        {
            "username": "wrong",
            "password": "wrong",
        },
    )

    assert response.status_code == 200
    assert "Credencials incorrectes".encode() in response.content


def test_dashboard_requires_login(db):
    response = Client().get(reverse("adm_dashboard"))
    assert response.status_code == 302


def test_dashboard_loads_for_staff(db):
    response = logged_client().get(reverse("adm_dashboard"))
    assert response.status_code == 200


def test_missions_page_loads(db):
    create_mission()
    response = logged_client().get(reverse("adm_missions"))

    assert response.status_code == 200
    assert b"Test Mission" in response.content


def test_mission_create_get_loads(db):
    response = logged_client().get(reverse("adm_mission_create"))
    assert response.status_code == 200


def test_mission_create_post_creates_mission(db):
    response = logged_client().post(
        reverse("adm_mission_create"),
        {
            "name": "Created Mission",
            "description": "desc",
            "action": "PLANT",
            "goal": "2",
            "rewardCoins": "5",
            "plant": "",
            "product": "",
            "plantReward": "",
            "productReward": "",
        },
    )

    assert response.status_code == 302
    assert Mission.objects.filter(name="Created Mission").exists()


def test_mission_edit_get_loads(db):
    mission = create_mission()

    response = logged_client().get(reverse("adm_mission_edit", args=[mission.name]))

    assert response.status_code == 200


def test_mission_edit_post_updates_mission(db):
    mission = create_mission()

    response = logged_client().post(
        reverse("adm_mission_edit", args=[mission.name]),
        {
            "description": "new desc",
            "action": "WATER",
            "goal": "3",
            "rewardCoins": "20",
            "plant": "",
            "product": "",
            "plantReward": "",
            "productReward": "",
        },
    )

    mission.refresh_from_db()

    assert response.status_code == 302
    assert mission.description == "new desc"
    assert mission.action == "WATER"
    assert mission.goal == 3
    assert mission.rewardCoins == 20


def test_mission_delete_post_deletes_mission(db):
    mission = create_mission()

    response = logged_client().post(reverse("adm_mission_delete", args=[mission.name]))

    assert response.status_code == 302
    assert not Mission.objects.filter(name=mission.name).exists()


def test_mission_assign_all_creates_user_missions(db):
    mission = create_mission()
    User.objects.create_user(username="normal_user", password="pass123")

    response = logged_client().post(reverse("adm_mission_assign", args=[mission.name]))

    assert response.status_code == 302
    assert UserMission.objects.filter(mission=mission).exists()


def test_products_page_loads(db):
    create_product()
    response = logged_client().get(reverse("adm_products"))

    assert response.status_code == 200
    assert b"Test Product" in response.content


def test_product_create_get_loads(db):
    response = logged_client().get(reverse("adm_product_create"))
    assert response.status_code == 200


def test_product_create_post_creates_product(db):
    response = logged_client().post(
        reverse("adm_product_create"),
        {
            "name": "Created Product",
            "description": "desc",
            "effectType": "growth",
            "price": "15",
            "rarity": "common",
            "isInstant": "on",
            "value": "2.5",
            "durationHours": "",
        },
    )

    assert response.status_code == 302
    assert Product.objects.filter(name="Created Product").exists()


def test_product_edit_get_loads(db):
    product = create_product()

    response = logged_client().get(reverse("adm_product_edit", args=[product.name]))

    assert response.status_code == 200


def test_product_edit_post_updates_product(db):
    product = create_product()

    response = logged_client().post(
        reverse("adm_product_edit", args=[product.name]),
        {
            "description": "new desc",
            "effectType": "health",
            "price": "30",
            "rarity": "rare",
            "isInstant": "on",
            "value": "5",
            "durationHours": "",
        },
    )

    product.refresh_from_db()

    assert response.status_code == 302
    assert product.description == "new desc"
    assert product.effectType == "health"
    assert product.price == 30
    assert product.rarity == "rare"


def test_product_delete_post_deletes_product(db):
    product = create_product()

    response = logged_client().post(reverse("adm_product_delete", args=[product.name]))

    assert response.status_code == 302
    assert not Product.objects.filter(name=product.name).exists()


def test_users_page_loads(db):
    response = logged_client().get(reverse("adm_users"))
    assert response.status_code == 200


def test_signout_redirects_to_signin(db):
    client = logged_client()

    response = client.post(reverse("adm_logout"))

    assert response.status_code == 302
