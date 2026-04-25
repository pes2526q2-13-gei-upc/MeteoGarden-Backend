import pytest
from unittest.mock import MagicMock, patch
from datetime import timedelta
from django.utils import timezone
from api.models import GrowthState, Product, ActiveProduct
from api.plant_simulation import apply_product, _apply_reading


@pytest.mark.django_db
class TestProductsLogicComprehensive:

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.inventory.products = {
            "Poció Vida": 1, "Fertilitzant": 1, "Escut": 1, "Fènix": 1
        }
        return user

    @pytest.fixture
    def plant_base(self):
        # Fem servir un MagicMock però amb atributs de dades reals
        plant = MagicMock()
        plant.id = 1  # ID numèric per evitar l'error de Django
        plant.healthLevel = 50.0
        plant.waterLevel = 50.0
        plant.growthPhase = GrowthState.SEED
        plant.plantedAt = timezone.now() - timedelta(hours=5)
        plant.diedAt = None
        plant.plant.minTemperature = 15.0
        plant.plant.maxTemperature = 25.0
        plant.plant.canFlower = True
        return plant

    # --- 1. LÒGICA D'APLICACIÓ DE PRODUCTES ---

    def test_apply_health_overflow(self, mock_user, plant_base):
        plant_base.healthLevel = 95.0
        with patch('api.models.Product.objects.get') as m:
            m.return_value = MagicMock(isInstant=True, effectType="health", value=20)
            apply_product(mock_user, plant_base, "Poció Vida")
            assert plant_base.healthLevel == 100.0

    def test_apply_growth_phase_jump(self, mock_user, plant_base):
        plant_base.growthPhase = GrowthState.SEED
        plant_base.healthLevel = 100.0
        # Simulem que el producte dóna 200 hores de cop
        with patch('api.models.Product.objects.get') as m:
            m.return_value = MagicMock(isInstant=True, effectType="growth", value=200)
            apply_product(mock_user, plant_base, "Fertilitzant")
            assert plant_base.growthPhase in (GrowthState.MATURE, GrowthState.FLOWERING)

    def test_apply_revive_logic(self, mock_user, plant_base):
        plant_base.growthPhase = GrowthState.DEAD
        plant_base.diedAt = timezone.now() - timedelta(hours=10)
        original_planted_at = plant_base.plantedAt

        with patch('api.models.Product.objects.get') as m:
            m.return_value = MagicMock(isInstant=True, effectType="revive")
            apply_product(mock_user, plant_base, "Fènix")
            assert plant_base.growthPhase != GrowthState.DEAD
            assert plant_base.plantedAt > original_planted_at

    # --- 2. LÒGICA DE SIMULACIÓ I PROTECCIONS ---

    def test_extreme_weather_damage_without_protection(self, plant_base):
        # IMPORTANT: timestamp ha de ser una data real, no un MagicMock
        reading = MagicMock()
        reading.temperature = 0.0
        reading.precipitation = 0.0
        reading.solarIrradiance = 200.0
        reading.windSpeed = 20.0
        reading.relativeHumidity = 60.0
        reading.timestamp = timezone.now()

        with patch('api.models.ActiveProduct.objects.filter') as mock_filter:
            mock_filter.return_value = []  # Cap protecció
            initial_health = plant_base.healthLevel
            _apply_reading(plant_base, reading, 1.0)
            assert plant_base.healthLevel < initial_health

    def test_combined_protections(self, plant_base):
        reading = MagicMock()
        reading.temperature = 20.0
        reading.precipitation = 0.0
        reading.solarIrradiance = 1000.0
        reading.windSpeed = 25.0
        reading.relativeHumidity = 20.0
        reading.timestamp = timezone.now()

        eff_sun = MagicMock()
        eff_sun.product.effectType = "sun_protection"
        eff_sun.is_active.return_value = True

        eff_wind = MagicMock()
        eff_wind.product.effectType = "wind_protection"
        eff_wind.is_active.return_value = True

        with patch('api.models.ActiveProduct.objects.filter') as mock_filter:
            mock_filter.return_value = [eff_sun, eff_wind]
            _apply_reading(plant_base, reading, 5.0)

            # L'aigua només hauria de baixar la base (4% * 5h = 20%) -> 50 - 20 = 30
            assert plant_base.waterLevel >= 30.0
            assert plant_base.healthLevel >= 50.0

    def test_dehydration_damage(self, plant_base):
        plant_base.waterLevel = 10.0
        reading = MagicMock()
        reading.temperature = 20.0
        reading.precipitation = 0.0
        reading.solarIrradiance = 200.0
        reading.windSpeed = 0.0
        reading.relativeHumidity = 60.0
        reading.timestamp = timezone.now()

        with patch('api.models.ActiveProduct.objects.filter') as mock_filter:
            mock_filter.return_value = []
            _apply_reading(plant_base, reading, 1.0)
            assert plant_base.healthLevel < 50.0

    def test_death_condition(self, plant_base):
        plant_base.healthLevel = 0.1
        reading = MagicMock()
        reading.temperature = -50.0
        reading.precipitation = 0.0
        reading.solarIrradiance = 200.0
        reading.windSpeed = 0.0
        reading.relativeHumidity = 60.0  # Afegim això per evitar el TypeError
        reading.timestamp = timezone.now()

        with patch('api.models.ActiveProduct.objects.filter') as mock_filter:
            mock_filter.return_value = []
            _apply_reading(plant_base, reading, 1.0)

            # Comprovem que la lògica de mort s'ha disparat
            assert plant_base.growthPhase == GrowthState.DEAD
            assert plant_base.healthLevel == 0.0

    def test_no_growth_if_unhealthy(self, plant_base):
        plant_base.healthLevel = 20.0  # < 30.0
        plant_base.growthPhase = GrowthState.SEED
        current_time = plant_base.plantedAt + timedelta(hours=100)

        # Cridem directament la funció de càlcul de fase
        from api.plant_simulation import _recalculate_phase
        new_phase = _recalculate_phase(plant_base, plant_base.healthLevel, current_time)

        assert new_phase == GrowthState.SEED