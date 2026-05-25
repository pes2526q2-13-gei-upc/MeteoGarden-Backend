from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from api.models import Mission, Product

User = get_user_model()


def create_staff():
    return User.objects.create_user(
        username="admin",
        password="admin123",
        is_staff=True,
    )


def test_signin_page_loads(db):
    client = Client()
    response = client.get(reverse("adm_signin"))

    assert response.status_code == 200


def test_dashboard_requires_login(db):
    client = Client()
    response = client.get(reverse("adm_dashboard"))

    assert response.status_code == 302


def test_dashboard_loads_for_staff(db):
    staff = create_staff()

    client = Client()
    client.login(username="admin", password="admin123")

    response = client.get(reverse("adm_dashboard"))

    assert response.status_code == 200


def test_missions_page_loads(db):
    staff = create_staff()

    Mission.objects.create(
        name="Test Mission",
        description="desc",
        action="PLANT",
        goal=1,
        rewardCoins=10,
    )

    client = Client()
    client.login(username="admin", password="admin123")

    response = client.get(reverse("adm_missions"))

    assert response.status_code == 200
    assert b"Test Mission" in response.content


def test_products_page_loads(db):
    staff = create_staff()

    Product.objects.create(
        name="Test Product",
        description="desc",
        effectType="growth",
        price=10,
        rarity="common",
        isInstant=True,
    )

    client = Client()
    client.login(username="admin", password="admin123")

    response = client.get(reverse("adm_products"))

    assert response.status_code == 200
    assert b"Test Product" in response.content
