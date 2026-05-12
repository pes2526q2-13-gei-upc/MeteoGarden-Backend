from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from api.models import Product, Shop


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

    def test_initialize_starter_stock_fills_products(self):
        """initialize_starter_stock carga los productos iniciales."""
        shop = Shop.get_solo()
        shop.initialize_starter_stock()

        self.assertEqual(shop.products, Shop.STARTER_PRODUCTS)

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

    # ------------------------------------------------------------------
    # Caso 3: producto en shop pero no en BD
    # -----------------------------------------
