from django.test import TestCase, Client

class UseProductAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="test", password="1234")

        self.client.force_login(self.user)

        self.product = Product.objects.create(
            name="Hydration Shield",
            effectType="water_protection",
            durationHours=24,
            isInstant=False,
            price=10
        )

        # crea plant amb pot/garden segons el teu model

        self.user.inventory = type("obj", (), {
            "products": ["Hydration Shield"],
            "removeProduct": lambda *args, **kwargs: None
        })()

    def test_use_product_returns_active_effect_data(self):
        response = self.client.post(
            "/api/use_product",
            data={
                "pot_id": 1,
                "product_name": "Hydration Shield"
            },
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["status"], "ok")
        self.assertFalse(data["isInstant"])
        self.assertIn("expiresAt", data)

    def test_missing_data_returns_400(self):
        response = self.client.post(
            "/api/use_product",
            data={},
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_plant_not_found_returns_404(self):
        response = self.client.post(
            "/api/use_product",
            data={
                "pot_id": 999,
                "product_name": "Hydration Shield"
            },
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 404)

    def test_product_not_found_returns_400(self):
        response = self.client.post(
            "/api/use_product",
            data={
                "pot_id": 1,
                "product_name": "Fake Product"
            },
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)