from django.test import TestCase
from django.contrib.auth import get_user_model
from api.models import Product, PlantInGarden, ActiveProduct
from api.plant_simulation import apply_product

User = get_user_model()


class ProductLogicTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test", password="1234")

        # crea planta fake (ajusta camps als teus)
        self.plant = PlantInGarden.objects.create(
            healthLevel=50,
            waterLevel=50,
            growthPhase="growth",
            plantedAt="2026-01-01T00:00:00Z",
        )

        # mock inventory (important!)
        self.user.inventory = type("obj", (), {
            "products": ["Small Heal", "Hydration Shield"],
            "removeProduct": lambda *args, **kwargs: None
        })()

    def test_instant_health_product(self):
        Product.objects.create(
            name="Small Heal",
            effectType="health",
            value=20,
            isInstant=True,
            price=10
        )

        apply_product(self.user, self.plant, "Small Heal")

        self.assertEqual(self.plant.healthLevel, 70)

    def test_non_instant_creates_active_product(self):
        product = Product.objects.create(
            name="Hydration Shield",
            effectType="water_protection",
            durationHours=24,
            isInstant=False,
            price=10
        )

        apply_product(self.user, self.plant, "Hydration Shield")

        active = ActiveProduct.objects.filter(plant=self.plant).first()

        self.assertIsNotNone(active)
        self.assertTrue(active.is_active())

    def test_same_product_replaces_previous(self):
        product = Product.objects.create(
            name="Hydration Shield",
            effectType="water_protection",
            durationHours=24,
            isInstant=False,
            price=10
        )

        apply_product(self.user, self.plant, "Hydration Shield")
        apply_product(self.user, self.plant, "Hydration Shield")

        self.assertEqual(
            ActiveProduct.objects.filter(plant=self.plant).count(),
            1
        )

#sim
from api.plant_simulation import _apply_reading
from api.models import WeatherReading

def test_hydration_shield_prevents_water_loss(self):
    product = Product.objects.create(
        name="Hydration Shield",
        effectType="water_protection",
        durationHours=24,
        isInstant=False,
        price=10
    )

    ActiveProduct.objects.create(
        plant=self.plant,
        product=product
    )

    reading = WeatherReading(
        temperature=30,
        precipitation=0,
        solarIrradiance=500,
        windSpeed=2,
        relativeHumidity=20
    )

    water_before = self.plant.waterLevel

    _apply_reading(self.plant, reading, 1.0)

    self.assertEqual(self.plant.waterLevel, water_before)