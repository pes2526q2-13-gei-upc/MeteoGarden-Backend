import json
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

import pytest
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from api.models import Inventory, Plant, Product, Shop, User
from api.views.views_shop import buy_item, get_shop

def make_user(username="testuser", password="pass1234"):
    user = User.objects.create_user(
        username=username,
        password=password,
        email=f"{username}@example.com",
        city="Barcelona",
        stationCode="0001",
    )
    Inventory.objects.get_or_create(user=user)
    return user

def make_product(name="health_potion", price=15, **kwargs):
    defaults = dict(
        description="Recupera salud",
        effectType="health",
        value=30,
        durationHours=0,
        price=price,
        isInstant=True,
        rarity="common",
    )
    defaults.update(kwargs)
    return Product.objects.get_or_create(name=name, defaults=defaults)[0]

class ShopModelTest(TestCase):
    """Tests unitarios del modelo Shop."""

    def setUp(self):
        Shop.objects.all().delete()

    # ------------------------------------------------------------------
    # get_solo
    # ------------------------------------------------------------------
    def test_get_solo_creates_shop_if_not_exists(self):
        """get_solo crea la tienda si no existe."""
        shop = Shop.get_solo()
        self.assertIsNotNone(shop)
        self.assertEqual(Shop.objects.count(), 1)

    def test_get_solo_returns_same_instance(self):
        """get_solo siempre devuelve la misma instancia."""
        shop1 = Shop.get_solo()
        shop2 = Shop.get_solo()
        self.assertEqual(shop1.pk, shop2.pk)

    def test_cannot_create_second_shop(self):
        """No se puede crear una segunda instancia de Shop."""
        Shop.get_solo()
        with self.assertRaises(Exception):
            Shop.objects.create()

    # ------------------------------------------------------------------
    # initialize_starter_stock
    # ------------------------------------------------------------------
    def test_initialize_starter_stock_fills_seeds(self):
        """initialize_starter_stock carga las semillas iniciales."""
        shop = Shop.get_solo()
        self.assertEqual(shop.seeds, {})

        shop.initialize_starter_stock()

        self.assertEqual(shop.seeds, Shop.STARTER_SEEDS)

    def test_initialize_starter_stock_does_not_overwrite_existing_seeds(self):
        """initialize_starter_stock no sobreescribe si ya hay seeds."""
        shop = Shop.get_solo()
        shop.seeds = {"custom_seed": 99}
        shop.save()

        shop.initialize_starter_stock()

        self.assertEqual(shop.seeds, {"custom_seed": 99})

    def test_initialize_starter_stock_does_not_overwrite_existing_products(self):
        """initialize_starter_stock no sobreescribe si ya hay products."""
        shop = Shop.get_solo()
        shop.products = {"custom_product": 50}
        shop.save()

        shop.initialize_starter_stock()

        self.assertEqual(shop.products, {"custom_product": 50})

    # ------------------------------------------------------------------
    # update_stock
    # ------------------------------------------------------------------
    def test_update_stock_adds_seed(self):
        """update_stock añade una semilla al stock."""
        shop = Shop.get_solo()
        shop.update_stock("seed", "rosa_canina", 5)

        self.assertIn("rosa_canina", shop.seeds)
        self.assertEqual(shop.seeds["rosa_canina"], 5)

    def test_update_stock_adds_product(self):
        """update_stock añade un producto al stock."""
        shop = Shop.get_solo()
        shop.update_stock("product", "health_potion", 15)

        self.assertIn("health_potion", shop.products)
        self.assertEqual(shop.products["health_potion"], 15)

    def test_update_stock_updates_existing_price(self):
        """update_stock actualiza el precio si el item ya existe."""
        shop = Shop.get_solo()
        shop.update_stock("seed", "rosa_canina", 5)
        shop.update_stock("seed", "rosa_canina", 10)

        self.assertEqual(shop.seeds["rosa_canina"], 10)

    # ------------------------------------------------------------------
    # remove_item
    # ------------------------------------------------------------------
    def test_remove_item_removes_seed(self):
        """remove_item elimina una semilla del stock."""
        shop = Shop.get_solo()
        shop.seeds = {"rosa_canina": 5}
        shop.save()

        shop.remove_item("seed", "rosa_canina")

        self.assertNotIn("rosa_canina", shop.seeds)

    def test_remove_item_removes_product(self):
        """remove_item elimina un producto del stock."""
        shop = Shop.get_solo()
        shop.products = {"health_potion": 15}
        shop.save()

        shop.remove_item("product", "health_potion")

        self.assertNotIn("health_potion", shop.products)

    def test_remove_item_does_nothing_if_not_found(self):
        """remove_item no falla si el item no existe."""
        shop = Shop.get_solo()
        try:
            shop.remove_item("seed", "nonexistent")
            shop.remove_item("product", "nonexistent")
        except Exception as e:
            self.fail(f"remove_item lanzó una excepción inesperada: {e}")


class ShopViewTest(TestCase):
    """Tests del endpoint GET /api/shop/."""

    def setUp(self):
        Shop.objects.all().delete()
        self.client = Client()

        self.product = Product.objects.create(
            name="health_potion",
            description="Recupera la salud instantáneamente",
            effectType="health",
            value=30,
            durationHours=0,
            price=15,
            isInstant=True,
        )

    # ------------------------------------------------------------------
    # Caso 1: respuesta básica OK
    # ------------------------------------------------------------------
    def test_get_shop_returns_200(self):
        """El endpoint devuelve 200."""
        response = self.client.get("/api/shop/")
        self.assertEqual(response.status_code, 200)

    def test_get_shop_returns_seeds_and_products(self):
        """La respuesta contiene las claves seeds y products."""
        response = self.client.get("/api/shop/")
        data = response.json()

        self.assertIn("seeds", data)
        self.assertIn("products", data)

    # ------------------------------------------------------------------
    # Caso 2: productos con imagen
    def test_product_with_image_returns_url(self):
        shop = Shop.get_solo()
        shop.products = {"health_potion": 15}
        shop.save()

        img_file = SimpleUploadedFile(
            "health_potion.webp", b"fake_image_data", content_type="image/webp"
        )
        self.product.image_url = img_file
        self.product.save()

        response = self.client.get("/api/shop/")
        data = response.json()
        product = next(p for p in data["products"] if p["name"] == "health_potion")
        self.assertIn("image_url", product)
        self.assertIsNotNone(product["image_url"])

    def test_product_without_image_returns_none(self):
        """Un producto sin imagen devuelve image_url como None."""
        shop = Shop.get_solo()
        shop.products = {"health_potion": 15}
        shop.save()

        response = self.client.get("/api/shop/")
        data = response.json()

        product = next(p for p in data["products"] if p["name"] == "health_potion")
        self.assertIsNone(product["image_url"])




    # ─────────────────────────────────────────────
    # GET /api/shop/ — updated behaviour
    # ─────────────────────────────────────────────

    class GetShopUpdatedTest(TestCase):
        """Tests para el endpoint GET /api/shop/ con la lógica nueva."""

        def setUp(self):
            Shop.objects.all().delete()
            Product.objects.all().delete()
            Plant.objects.all().delete()
            self.client = Client()

        # ── Products: now ALL products in DB, not just those in shop.products ──

        def test_all_db_products_returned_regardless_of_shop_products_field(self):
            """Devuelve todos los productos de la BD, sin filtrar por shop.products."""
            make_product("health_potion", price=15)
            make_product("sun_lamp", price=20, effectType="sun")

            response = self.client.get("/api/shop/")
            names = [p["name"] for p in response.json()["products"]]

            self.assertIn("health_potion", names)
            self.assertIn("sun_lamp", names)

        def test_product_not_in_shop_products_field_still_returned(self):
            """Un producto que no está en shop.products sigue apareciendo."""
            shop = Shop.get_solo()
            shop.products = {}  # vacío a propósito
            shop.save()
            make_product("growth_serum", price=25, effectType="growth")

            response = self.client.get("/api/shop/")
            names = [p["name"] for p in response.json()["products"]]
            self.assertIn("growth_serum", names)

        def test_products_include_rarity_field(self):
            """Cada producto devuelve el campo rarity."""
            make_product("rare_gem", price=50, rarity="rare")

            response = self.client.get("/api/shop/")
            product = next(p for p in response.json()["products"] if p["name"] == "rare_gem")
            self.assertIn("rarity", product)
            self.assertEqual(product["rarity"], "rare")

        def test_products_include_all_expected_fields(self):
            """Cada producto devuelve todos los campos requeridos."""
            make_product("potion", price=10)

            response = self.client.get("/api/shop/")
            product = next(p for p in response.json()["products"] if p["name"] == "potion")
            for field in ("name", "description", "effectType", "value", "durationHours",
                          "isInstant", "price", "image_url", "rarity"):
                self.assertIn(field, product, msg=f"Campo ausente: {field}")

        def test_no_products_in_db_returns_empty_list(self):
            """Si no hay productos en BD, products es una lista vacía."""
            response = self.client.get("/api/shop/")
            self.assertEqual(response.json()["products"], [])

        # ── Seeds: only seeds whose Plant exists in DB ──

        def test_seed_with_no_plant_in_db_is_skipped(self):
            """Una semilla cuya planta no existe en BD se omite silenciosamente."""
            shop = Shop.get_solo()
            shop.seeds = {"ghost_plant": 5}
            shop.save()

            response = self.client.get("/api/shop/")
            scientific_names = [s["scientificName"] for s in response.json()["seeds"]]
            self.assertNotIn("ghost_plant", scientific_names)

        def test_seed_with_plant_in_db_is_returned(self):
            """Una semilla cuya planta existe en BD aparece en la respuesta."""
            plant = Plant.objects.create(
                scientificName="rosa_canina",
                commonName="Rosa silvestre",
                family="Rosaceae",
                minTemperature=5.0,
                maxTemperature=35.0,
            )
            shop = Shop.get_solo()
            shop.seeds = {"rosa_canina": 8}
            shop.save()

            response = self.client.get("/api/shop/")
            seeds = response.json()["seeds"]
            self.assertTrue(any(s["scientificName"] == "rosa_canina" for s in seeds))

        def test_seed_response_contains_plant_metadata(self):
            """La semilla devuelta incluye commonName, family y description."""
            Plant.objects.create(
                scientificName="dahlia_pinnata",
                commonName="Dalia",
                family="Asteraceae",
                description="Flor ornamental",
                minTemperature=10.0,
                maxTemperature=38.0,
            )
            shop = Shop.get_solo()
            shop.seeds = {"dahlia_pinnata": 3}
            shop.save()

            response = self.client.get("/api/shop/")
            seed = next(s for s in response.json()["seeds"] if s["scientificName"] == "dahlia_pinnata")
            self.assertEqual(seed["commonName"], "Dalia")
            self.assertEqual(seed["family"], "Asteraceae")
            self.assertEqual(seed["description"], "Flor ornamental")

        def test_seed_price_matches_shop_seeds_dict(self):
            """El precio de la semilla es el valor guardado en shop.seeds."""
            Plant.objects.create(
                scientificName="orchidaceae",
                minTemperature=15.0,
                maxTemperature=35.0,
            )
            shop = Shop.get_solo()
            shop.seeds = {"orchidaceae": 99}
            shop.save()

            response = self.client.get("/api/shop/")
            seed = next(s for s in response.json()["seeds"] if s["scientificName"] == "orchidaceae")
            self.assertEqual(seed["price"], 99)

        def test_mixed_seeds_some_with_plant_some_without(self):
            """Solo se devuelven las semillas cuya planta existe en BD."""
            Plant.objects.create(
                scientificName="real_plant",
                minTemperature=5.0,
                maxTemperature=40.0,
            )
            shop = Shop.get_solo()
            shop.seeds = {"real_plant": 5, "fake_plant": 5}
            shop.save()

            response = self.client.get("/api/shop/")
            names = [s["scientificName"] for s in response.json()["seeds"]]
            self.assertIn("real_plant", names)
            self.assertNotIn("fake_plant", names)

        def test_get_shop_calls_initialize_starter_stock(self):
            """El endpoint llama a initialize_starter_stock (rellena seeds si están vacíos)."""
            Shop.get_solo()  # crea la tienda sin seeds

            response = self.client.get("/api/shop/")
            shop = Shop.get_solo()
            self.assertEqual(shop.seeds, Shop.STARTER_SEEDS)

    # ─────────────────────────────────────────────
    # POST /api/shop/<username>/buy/ — buy_item
    # ─────────────────────────────────────────────

    class BuyItemTest(TestCase):
        """Tests para el endpoint POST /api/shop/<username>/buy/."""

        def setUp(self):
            Shop.objects.all().delete()
            self.shop = Shop.get_solo()
            self.shop.seeds = {"rosa_canina": 5}
            self.shop.save()

            self.product = make_product("health_potion", price=15)
            self.user = make_user()
            self.inventory = Inventory.objects.get(user=self.user)
            self.inventory.coins = 100
            self.inventory.save()

            self.client = Client()
            self.client.force_login(self.user)

        # ── Happy paths ──

        def test_buy_seed_returns_200(self):
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "seed", "name": "rosa_canina"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        def test_buy_seed_deducts_coins(self):
            self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "seed", "name": "rosa_canina"}),
                content_type="application/json",
            )
            self.inventory.refresh_from_db()
            self.assertEqual(self.inventory.coins, 95)  # 100 - 5

        def test_buy_seed_adds_to_inventory(self):
            self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "seed", "name": "rosa_canina"}),
                content_type="application/json",
            )
            self.inventory.refresh_from_db()
            self.assertEqual(self.inventory.seeds.get("rosa_canina"), 1)

        def test_buy_seed_stacks_with_existing(self):
            self.inventory.seeds = {"rosa_canina": 3}
            self.inventory.save()
            self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "seed", "name": "rosa_canina"}),
                content_type="application/json",
            )
            self.inventory.refresh_from_db()
            self.assertEqual(self.inventory.seeds["rosa_canina"], 4)

        def test_buy_product_returns_200(self):
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "product", "name": "health_potion"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        def test_buy_product_deducts_product_price_from_db(self):
            """El precio del producto viene de Product.price, no de shop.products."""
            self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "product", "name": "health_potion"}),
                content_type="application/json",
            )
            self.inventory.refresh_from_db()
            self.assertEqual(self.inventory.coins, 85)  # 100 - 15

        def test_buy_product_adds_to_inventory(self):
            self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "product", "name": "health_potion"}),
                content_type="application/json",
            )
            self.inventory.refresh_from_db()
            self.assertEqual(self.inventory.products.get("health_potion"), 1)

        def test_buy_product_stacks_with_existing(self):
            self.inventory.products = {"health_potion": 2}
            self.inventory.save()
            self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "product", "name": "health_potion"}),
                content_type="application/json",
            )
            self.inventory.refresh_from_db()
            self.assertEqual(self.inventory.products["health_potion"], 3)

        def test_buy_response_includes_coins_remaining(self):
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "product", "name": "health_potion"}),
                content_type="application/json",
            )
            data = response.json()
            self.assertIn("coins_remaining", data)
            self.assertEqual(data["coins_remaining"], 85)

        # ── Authentication ──

        def test_unauthenticated_returns_401(self):
            anon = Client()
            response = anon.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "product", "name": "health_potion"}),
                content_type="application/json",
            )
            self.assertIn(response.status_code, (401, 403))

        # ── Error: not enough coins ──

        def test_insufficient_coins_returns_400(self):
            self.inventory.coins = 3
            self.inventory.save()
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "seed", "name": "rosa_canina"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("coins", response.json().get("error", "").lower())

        def test_insufficient_coins_does_not_modify_inventory(self):
            self.inventory.coins = 1
            self.inventory.save()
            self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "product", "name": "health_potion"}),
                content_type="application/json",
            )
            self.inventory.refresh_from_db()
            self.assertEqual(self.inventory.coins, 1)
            self.assertNotIn("health_potion", self.inventory.products)

        def test_exact_coins_allows_purchase(self):
            self.inventory.coins = 5  # precio exacto de rosa_canina
            self.inventory.save()
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "seed", "name": "rosa_canina"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.inventory.refresh_from_db()
            self.assertEqual(self.inventory.coins, 0)

        # ── Error: item not found ──

        def test_seed_not_in_shop_returns_404(self):
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "seed", "name": "nonexistent_seed"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 404)

        def test_product_not_in_db_returns_404(self):
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "product", "name": "nonexistent_product"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 404)

        # ── Error: bad request body ──

        def test_invalid_type_returns_400(self):
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "weapon", "name": "health_potion"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)

        def test_missing_type_returns_400(self):
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"name": "health_potion"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)

        def test_missing_name_returns_400(self):
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data=json.dumps({"type": "product"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)

        def test_invalid_json_returns_400(self):
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data="not json at all",
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)

        def test_empty_body_returns_400(self):
            response = self.client.post(
                f"/api/shop/{self.user.username}/buy/",
                data="{}",
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)

        # ── Error: user not found ──

        def test_unknown_user_returns_404(self):
            response = self.client.post(
                "/api/shop/nobody/buy/",
                data=json.dumps({"type": "product", "name": "health_potion"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 404)

@pytest.mark.django_db
class TestShopViewMissingCoverage:
    def create_user_with_inventory(self, username="testuser", coins=100):
        user = User.objects.create_user(username=username, password="testpass")

        inventory, _ = Inventory.objects.get_or_create(
            user=user,
            defaults={
                "coins": coins,
                "seeds": {},
                "products": {},
            },
        )

        inventory.coins = coins
        inventory.seeds = {}
        inventory.products = {}
        inventory.save()

        return user, inventory

    def create_product(
        self,
        name="Magic Potion",
        price=20,
        description="Potion description",
        effect_type="growth",
        value=10,
        duration_hours=2,
        is_instant=False,
        rarity="common",
    ):
        return Product.objects.create(
            name=name,
            description=description,
            effectType=effect_type,
            value=value,
            durationHours=duration_hours,
            isInstant=is_instant,
            price=price,
            rarity=rarity,
        )

    def test_get_shop_returns_seed_when_matching_plant_exists(self, monkeypatch):
        shop = Shop.get_solo()
        shop.seeds = {"rosa_rugosa": 15}
        shop.save()

        monkeypatch.setattr(Shop, "initialize_starter_stock", lambda self: None)

        Plant.objects.create(
            scientificName="rosa_rugosa",
            commonName="Rosa rugosa",
            family="Rosaceae",
            description="A flowering plant.",
            minTemperature=5,
            maxTemperature=30,
            canFlower=True,
        )

        request = RequestFactory().get("/shop/")
        response = get_shop(request)

        assert response.status_code == 200

        data = json.loads(response.content)

        assert "seeds" in data
        assert len(data["seeds"]) == 1
        assert data["seeds"][0]["scientificName"] == "rosa_rugosa"
        assert data["seeds"][0]["commonName"] == "Rosa rugosa"
        assert data["seeds"][0]["family"] == "Rosaceae"
        assert data["seeds"][0]["description"] == "A flowering plant."
        assert data["seeds"][0]["price"] == 15

    def test_buy_seed_success(self):
        user, inventory = self.create_user_with_inventory(coins=100)

        shop = Shop.get_solo()
        shop.seeds = {"rosa_rugosa": 25}
        shop.save()

        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data=json.dumps({"type": "seed", "name": "rosa_rugosa"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = buy_item(request, username=user.username)

        assert response.status_code == 200

        data = json.loads(response.content)
        assert data["message"] == "seed 'rosa_rugosa' bought successfully"
        assert data["coins_remaining"] == 75

        inventory.refresh_from_db()
        assert inventory.coins == 75
        assert inventory.seeds["rosa_rugosa"] == 1

    def test_buy_product_success(self):
        user, inventory = self.create_user_with_inventory(coins=100)
        self.create_product(name="Growth Potion", price=30)

        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data=json.dumps({"type": "product", "name": "Growth Potion"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = buy_item(request, username=user.username)

        assert response.status_code == 200

        data = json.loads(response.content)
        assert data["message"] == "product 'Growth Potion' bought successfully"
        assert data["coins_remaining"] == 70

        inventory.refresh_from_db()
        assert inventory.coins == 70
        assert inventory.products["Growth Potion"] == 1

    def test_buy_item_invalid_json_returns_400(self):
        user, _ = self.create_user_with_inventory(coins=100)

        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data="{invalid-json",
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = buy_item(request, username=user.username)

        assert response.status_code == 400

        data = json.loads(response.content)
        assert data["error"] == "Invalid body"

    def test_buy_item_missing_type_returns_400(self):
        user, _ = self.create_user_with_inventory(coins=100)

        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data=json.dumps({"name": "rosa_rugosa"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = buy_item(request, username=user.username)

        assert response.status_code == 400

        data = json.loads(response.content)
        assert data["error"] == "Missing 'type' or 'name'"

    def test_buy_item_missing_name_returns_400(self):
        user, _ = self.create_user_with_inventory(coins=100)

        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data=json.dumps({"type": "seed"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = buy_item(request, username=user.username)

        assert response.status_code == 400

        data = json.loads(response.content)
        assert data["error"] == "Missing 'type' or 'name'"

    def test_buy_seed_not_found_returns_404(self):
        user, inventory = self.create_user_with_inventory(coins=100)

        shop = Shop.get_solo()
        shop.seeds = {"rosa_rugosa": 25}
        shop.save()

        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data=json.dumps({"type": "seed", "name": "unknown_seed"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = buy_item(request, username=user.username)

        assert response.status_code == 404

        data = json.loads(response.content)
        assert data["error"] == "Seed not found in shop"

        inventory.refresh_from_db()
        assert inventory.coins == 100
        assert inventory.seeds == {}

    def test_buy_product_not_found_returns_404(self):
        user, inventory = self.create_user_with_inventory(coins=100)

        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data=json.dumps({"type": "product", "name": "Unknown Product"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = buy_item(request, username=user.username)

        assert response.status_code == 404

        data = json.loads(response.content)
        assert data["error"] == "Product not found"

        inventory.refresh_from_db()
        assert inventory.coins == 100
        assert inventory.products == {}

    def test_buy_item_invalid_type_returns_400(self):
        user, _ = self.create_user_with_inventory(coins=100)

        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data=json.dumps({"type": "invalid", "name": "rosa_rugosa"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = buy_item(request, username=user.username)

        assert response.status_code == 400

        data = json.loads(response.content)
        assert data["error"] == "Invalid type, must be 'seed' or 'product'"

    def test_buy_seed_not_enough_coins_returns_400(self):
        user, inventory = self.create_user_with_inventory(coins=5)

        shop = Shop.get_solo()
        shop.seeds = {"rosa_rugosa": 25}
        shop.save()

        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data=json.dumps({"type": "seed", "name": "rosa_rugosa"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = buy_item(request, username=user.username)

        assert response.status_code == 400

        data = json.loads(response.content)
        assert data["error"] == "Not enough coins"

        inventory.refresh_from_db()
        assert inventory.coins == 5
        assert inventory.seeds == {}

    def test_buy_product_not_enough_coins_returns_400(self):
        user, inventory = self.create_user_with_inventory(coins=5)
        self.create_product(name="Expensive Potion", price=50)

        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data=json.dumps({"type": "product", "name": "Expensive Potion"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = buy_item(request, username=user.username)

        assert response.status_code == 400

        data = json.loads(response.content)
        assert data["error"] == "Not enough coins"

        inventory.refresh_from_db()
        assert inventory.coins == 5
        assert inventory.products == {}

    def test_buy_item_user_not_found_returns_404(self):
        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data=json.dumps({"type": "seed", "name": "rosa_rugosa"}),
            content_type="application/json",
        )

        fake_user = User.objects.create_user(username="authenticated_user", password="testpass")
        force_authenticate(request, user=fake_user)

        response = buy_item(request, username="missing_user")

        assert response.status_code == 404

    def test_buy_item_inventory_not_found_returns_404(self):
        user = User.objects.create_user(username="user_without_inventory", password="testpass")

        factory = APIRequestFactory()
        request = factory.post(
            "/shop/buy/",
            data=json.dumps({"type": "seed", "name": "rosa_rugosa"}),
            content_type="application/json",
        )
        force_authenticate(request, user=user)

        response = buy_item(request, username=user.username)

        assert response.status_code == 404