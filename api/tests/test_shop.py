import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from api.models import Image, Inventory, Plant, Product, Shop, User
from api.views.views_shop import (
    buy_item,
    get_shop_product,
    get_shop_products,
    get_shop_seed,
    get_shop_seeds,
)


def make_user(username="testuser", password="pass1234"):
    user = User.objects.create_user(
        username=username,
        password=password,
        email=f"{username}@example.com",
        city="Barcelona",
        stationCode="0001",
        language="en",
    )

    Inventory.objects.get_or_create(
        user=user,
        defaults={
            "coins": 100,
            "seeds": {},
            "products": {},
        },
    )

    return user


def make_product(name="health_potion", price=15, **kwargs):
    defaults = dict(
        description="Recovers health",
        effectType="health",
        value=30,
        durationHours=0,
        price=price,
        isInstant=True,
        rarity="common",
    )

    defaults.update(kwargs)

    return Product.objects.create(
        name=name,
        **defaults,
    )


class ShopModelTest(TestCase):
    def setUp(self):
        Shop.objects.all().delete()

    def test_get_solo_creates_shop(self):
        shop = Shop.get_solo()

        self.assertIsNotNone(shop)
        self.assertEqual(Shop.objects.count(), 1)

    def test_get_solo_returns_same_instance(self):
        shop1 = Shop.get_solo()
        shop2 = Shop.get_solo()

        self.assertEqual(shop1.pk, shop2.pk)

    def test_initialize_starter_stock_fills_seeds(self):
        shop = Shop.get_solo()

        self.assertEqual(shop.seeds, {})

        shop.initialize_starter_stock()

        self.assertEqual(shop.seeds, Shop.STARTER_SEEDS)

    def test_initialize_starter_stock_does_not_overwrite(self):
        shop = Shop.get_solo()

        shop.seeds = {"custom_seed": 99}
        shop.save()

        shop.initialize_starter_stock()

        self.assertEqual(shop.seeds, {"custom_seed": 99})

    def test_update_stock_seed(self):
        shop = Shop.get_solo()

        shop.update_stock("seed", "rosa_canina", 5)

        self.assertEqual(shop.seeds["rosa_canina"], 5)

    def test_update_stock_product(self):
        shop = Shop.get_solo()

        shop.update_stock("product", "health_potion", 15)

        self.assertEqual(shop.products["health_potion"], 15)

    def test_remove_seed(self):
        shop = Shop.get_solo()

        shop.seeds = {"rosa_canina": 5}
        shop.save()

        shop.remove_item("seed", "rosa_canina")

        self.assertNotIn("rosa_canina", shop.seeds)

    def test_remove_product(self):
        shop = Shop.get_solo()

        shop.products = {"health_potion": 15}
        shop.save()

        shop.remove_item("product", "health_potion")

        self.assertNotIn("health_potion", shop.products)


class ShopProductsViewTest(TestCase):
    def setUp(self):
        Shop.objects.all().delete()

        self.client = APIClient()

        self.user = make_user("alice")

        self.client.force_authenticate(user=self.user)

    def test_get_shop_products_returns_200(self):
        response = self.client.get(
            reverse("get_shop_products"),
        )

        self.assertEqual(response.status_code, 200)

    def test_get_shop_products_returns_empty_list(self):
        response = self.client.get(
            reverse("get_shop_products"),
        )

        self.assertEqual(response.json(), [])

    def test_get_shop_products_returns_all_products(self):
        make_product("health_potion")
        make_product("sun_lamp", effectType="sun")

        response = self.client.get(
            reverse("get_shop_products"),
        )

        data = response.json()

        names = [p["name"] for p in data]

        self.assertIn("health_potion", names)
        self.assertIn("sun_lamp", names)

    def test_product_contains_required_fields(self):
        make_product("health_potion")

        response = self.client.get(
            reverse("get_shop_products"),
        )

        product = response.json()[0]

        for field in (
            "name",
            "displayName",
            "price",
            "image_url",
            "rarity",
        ):
            self.assertIn(field, product)

    def test_product_with_image_returns_url(self):
        product = make_product("health_potion")

        img = SimpleUploadedFile(
            "health.webp",
            b"fake_image",
            content_type="image/webp",
        )

        product.image_url = img
        product.save()

        response = self.client.get(
            reverse("get_shop_products"),
        )

        product_data = response.json()[0]

        self.assertIsNotNone(product_data["image_url"])

    def test_product_without_image_returns_none(self):
        make_product("health_potion")

        response = self.client.get(
            reverse("get_shop_products"),
        )

        product_data = response.json()[0]

        self.assertIsNone(product_data["image_url"])

    def test_unauthenticated_returns_401_or_403(self):
        client = APIClient()

        response = client.get(
            reverse("get_shop_products"),
        )

        self.assertIn(response.status_code, (401, 403))


class ShopProductDetailViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = make_user("alice")

        self.client.force_authenticate(user=self.user)

    def test_get_shop_product_returns_200(self):
        make_product("health_potion")

        response = self.client.get(
            reverse(
                "get_shop_product",
                kwargs={"name": "health_potion"},
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_get_shop_product_returns_expected_fields(self):
        make_product("health_potion")

        response = self.client.get(
            reverse(
                "get_shop_product",
                kwargs={"name": "health_potion"},
            )
        )

        data = response.json()

        for field in (
            "name",
            "displayName",
            "description",
            "effectType",
            "value",
            "durationHours",
            "isInstant",
            "price",
            "rarity",
            "image_url",
        ):
            self.assertIn(field, data)

    def test_get_shop_product_returns_404(self):
        response = self.client.get(
            reverse(
                "get_shop_product",
                kwargs={"name": "missing_product"},
            )
        )

        self.assertEqual(response.status_code, 404)


class ShopSeedsViewTest(TestCase):
    def setUp(self):
        Shop.objects.all().delete()

        self.client = APIClient()

        self.user = make_user("alice")

        self.client.force_authenticate(user=self.user)

    def test_get_shop_seeds_returns_200(self):
        response = self.client.get(
            reverse("get_shop_seeds"),
        )

        self.assertEqual(response.status_code, 200)

    def test_seed_with_existing_plant_is_returned(self):
        Plant.objects.create(
            scientificName="rosa_rugosa",
            commonName="Rose",
            family="Rosaceae",
            minTemperature=5,
            maxTemperature=30,
        )

        shop = Shop.get_solo()

        shop.seeds = {"rosa_rugosa": 5}
        shop.save()

        response = self.client.get(
            reverse("get_shop_seeds"),
        )

        data = response.json()

        self.assertEqual(len(data), 1)

        self.assertEqual(
            data[0]["scientificName"],
            "rosa_rugosa",
        )

    def test_seed_without_plant_is_skipped(self):
        shop = Shop.get_solo()

        shop.seeds = {"ghost_seed": 5}
        shop.save()

        response = self.client.get(
            reverse("get_shop_seeds"),
        )

        self.assertEqual(response.json(), [])

    def test_seed_contains_expected_fields(self):
        Plant.objects.create(
            scientificName="rosa_rugosa",
            commonName="Rose",
            family="Rosaceae",
            minTemperature=5,
            maxTemperature=30,
        )

        shop = Shop.get_solo()

        shop.seeds = {"rosa_rugosa": 5}
        shop.save()

        response = self.client.get(
            reverse("get_shop_seeds"),
        )

        seed = response.json()[0]

        for field in (
            "scientificName",
            "commonName",
            "price",
            "image_url",
        ):
            self.assertIn(field, seed)

    def test_seed_image_is_returned(self):
        plant = Plant.objects.create(
            scientificName="rosa_rugosa",
            commonName="Rose",
            family="Rosaceae",
            minTemperature=5,
            maxTemperature=30,
        )

        image_file = SimpleUploadedFile(
            "seed.webp",
            b"fake_image",
            content_type="image/webp",
        )

        Image.objects.create(
            plant=plant,
            growthPhase="seed",
            url=image_file,
        )

        shop = Shop.get_solo()

        shop.seeds = {"rosa_rugosa": 5}
        shop.save()

        response = self.client.get(
            reverse("get_shop_seeds"),
        )

        seed = response.json()[0]

        self.assertIsNotNone(seed["image_url"])

    def test_seed_without_image_returns_none(self):
        Plant.objects.create(
            scientificName="rosa_rugosa",
            commonName="Rose",
            family="Rosaceae",
            minTemperature=5,
            maxTemperature=30,
        )

        shop = Shop.get_solo()

        shop.seeds = {"rosa_rugosa": 5}
        shop.save()

        response = self.client.get(
            reverse("get_shop_seeds"),
        )

        seed = response.json()[0]

        self.assertIsNone(seed["image_url"])


class ShopSeedDetailViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = make_user("alice")

        self.client.force_authenticate(user=self.user)

    def test_get_shop_seed_returns_200(self):
        Plant.objects.create(
            scientificName="rosa_rugosa",
            commonName="Rose",
            family="Rosaceae",
            description="Flower",
            minTemperature=5,
            maxTemperature=30,
        )

        shop = Shop.get_solo()

        shop.seeds = {"rosa_rugosa": 5}
        shop.save()

        response = self.client.get(
            reverse(
                "get_shop_seed",
                kwargs={"scientific_name": "rosa_rugosa"},
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_get_shop_seed_returns_expected_fields(self):
        Plant.objects.create(
            scientificName="rosa_rugosa",
            commonName="Rose",
            family="Rosaceae",
            description="Flower",
            minTemperature=5,
            maxTemperature=30,
        )

        shop = Shop.get_solo()

        shop.seeds = {"rosa_rugosa": 5}
        shop.save()

        response = self.client.get(
            reverse(
                "get_shop_seed",
                kwargs={"scientific_name": "rosa_rugosa"},
            )
        )

        data = response.json()

        for field in (
            "scientificName",
            "commonName",
            "family",
            "description",
            "price",
        ):
            self.assertIn(field, data)

    def test_get_shop_seed_returns_404_if_not_in_shop(self):
        response = self.client.get(
            reverse(
                "get_shop_seed",
                kwargs={"scientific_name": "ghost_seed"},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_get_shop_seed_returns_404_if_plant_missing(self):
        shop = Shop.get_solo()

        shop.seeds = {"ghost_seed": 5}
        shop.save()

        response = self.client.get(
            reverse(
                "get_shop_seed",
                kwargs={"scientific_name": "ghost_seed"},
            )
        )

        self.assertEqual(response.status_code, 404)


class BuyItemTest(TestCase):
    def setUp(self):
        Shop.objects.all().delete()

        self.shop = Shop.get_solo()

        self.shop.seeds = {
            "rosa_rugosa": 5,
        }

        self.shop.save()

        self.product = make_product(
            "health_potion",
            price=15,
        )

        self.user = make_user()

        self.inventory = Inventory.objects.get(
            user=self.user,
        )

        self.inventory.coins = 100
        self.inventory.save()

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.user,
        )

    def buy_url(self):
        return reverse(
            "buy_item",
            kwargs={
                "username": self.user.username,
            },
        )

    def test_buy_seed_returns_200(self):
        response = self.client.post(
            self.buy_url(),
            data={
                "type": "seed",
                "name": "rosa_rugosa",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_buy_seed_deducts_coins(self):
        self.client.post(
            self.buy_url(),
            data={
                "type": "seed",
                "name": "rosa_rugosa",
            },
            format="json",
        )

        self.inventory.refresh_from_db()

        self.assertEqual(self.inventory.coins, 95)

    def test_buy_seed_adds_inventory(self):
        self.client.post(
            self.buy_url(),
            data={
                "type": "seed",
                "name": "rosa_rugosa",
            },
            format="json",
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.seeds["rosa_rugosa"],
            1,
        )

    def test_buy_seed_stacks(self):
        self.inventory.seeds = {
            "rosa_rugosa": 3,
        }

        self.inventory.save()

        self.client.post(
            self.buy_url(),
            data={
                "type": "seed",
                "name": "rosa_rugosa",
            },
            format="json",
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.seeds["rosa_rugosa"],
            4,
        )

    def test_buy_product_returns_200(self):
        response = self.client.post(
            self.buy_url(),
            data={
                "type": "product",
                "name": "health_potion",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_buy_product_deducts_coins(self):
        self.client.post(
            self.buy_url(),
            data={
                "type": "product",
                "name": "health_potion",
            },
            format="json",
        )

        self.inventory.refresh_from_db()

        self.assertEqual(self.inventory.coins, 85)

    def test_buy_product_adds_inventory(self):
        self.client.post(
            self.buy_url(),
            data={
                "type": "product",
                "name": "health_potion",
            },
            format="json",
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.products["health_potion"],
            1,
        )

    def test_buy_product_stacks(self):
        self.inventory.products = {
            "health_potion": 2,
        }

        self.inventory.save()

        self.client.post(
            self.buy_url(),
            data={
                "type": "product",
                "name": "health_potion",
            },
            format="json",
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.products["health_potion"],
            3,
        )

    def test_buy_response_contains_coins_remaining(self):
        response = self.client.post(
            self.buy_url(),
            data={
                "type": "product",
                "name": "health_potion",
            },
            format="json",
        )

        data = response.json()

        self.assertIn("coins_remaining", data)

        self.assertEqual(data["coins_remaining"], 85)

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            self.buy_url(),
            data="invalid json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_type_returns_400(self):
        response = self.client.post(
            self.buy_url(),
            data={
                "name": "health_potion",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_name_returns_400(self):
        response = self.client.post(
            self.buy_url(),
            data={
                "type": "product",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_type_returns_400(self):
        response = self.client.post(
            self.buy_url(),
            data={
                "type": "weapon",
                "name": "gun",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_seed_not_found_returns_404(self):
        response = self.client.post(
            self.buy_url(),
            data={
                "type": "seed",
                "name": "ghost_seed",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_product_not_found_returns_404(self):
        response = self.client.post(
            self.buy_url(),
            data={
                "type": "product",
                "name": "ghost_product",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_not_enough_coins_returns_400(self):
        self.inventory.coins = 1
        self.inventory.save()

        response = self.client.post(
            self.buy_url(),
            data={
                "type": "product",
                "name": "health_potion",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_exact_coins_allows_purchase(self):
        self.inventory.coins = 15
        self.inventory.save()

        response = self.client.post(
            self.buy_url(),
            data={
                "type": "product",
                "name": "health_potion",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.inventory.refresh_from_db()

        self.assertEqual(self.inventory.coins, 0)

    def test_unknown_user_returns_404(self):
        response = self.client.post(
            reverse(
                "buy_item",
                kwargs={
                    "username": "ghost_user",
                },
            ),
            data={
                "type": "product",
                "name": "health_potion",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_returns_401_or_403(self):
        client = APIClient()

        response = client.post(
            self.buy_url(),
            data={
                "type": "product",
                "name": "health_potion",
            },
            format="json",
        )

        self.assertIn(response.status_code, (401, 403))


@pytest.mark.django_db
class ShopDirectViewCoverageTest:
    def test_get_shop_products_direct_view(self):
        user = make_user("direct_user")

        make_product("health_potion")

        factory = APIRequestFactory()

        request = factory.get("/api/shop/products/")

        force_authenticate(request, user=user)

        response = get_shop_products(request)

        assert response.status_code == 200

    def test_get_shop_seeds_direct_view(self):
        user = make_user("direct_user2")

        Plant.objects.create(
            scientificName="rosa_rugosa",
            commonName="Rose",
            family="Rosaceae",
            minTemperature=5,
            maxTemperature=30,
        )

        shop = Shop.get_solo()

        shop.seeds = {
            "rosa_rugosa": 5,
        }

        shop.save()

        factory = APIRequestFactory()

        request = factory.get("/api/shop/seeds/")

        force_authenticate(request, user=user)

        response = get_shop_seeds(request)

        assert response.status_code == 200

    def test_get_shop_product_direct_view_404(self):
        user = make_user("direct_user3")

        factory = APIRequestFactory()

        request = factory.get("/api/shop/products/missing/")

        force_authenticate(request, user=user)

        response = get_shop_product(
            request,
            "missing",
        )

        assert response.status_code == 404

    def test_get_shop_seed_direct_view_404(self):
        user = make_user("direct_user4")

        factory = APIRequestFactory()

        request = factory.get("/api/shop/seeds/missing/")

        force_authenticate(request, user=user)

        response = get_shop_seed(
            request,
            "missing",
        )

        assert response.status_code == 404

    def test_buy_item_invalid_body_direct(self):
        user = make_user("direct_user5")

        factory = APIRequestFactory()

        request = factory.post(
            "/api/users/test/buy/",
            data="{bad json",
            content_type="application/json",
        )

        force_authenticate(request, user=user)

        response = buy_item(
            request,
            username=user.username,
        )

        assert response.status_code == 400
