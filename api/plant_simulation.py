from django.utils import timezone

from .models import GrowthState, PlantInGarden, Station, WeatherReading

# Paràmetres de simulació

BASE_WATER_LOSS_PER_HOUR = 4.0  # % d'aigua perduda/hora en condicions normals

RAIN_THRESHOLD_MM = 0.1  # mm per lectura per considerar que plou
RAIN_MM_TO_WATER_PERCENT = 4.5  # cada mm de pluja = +4.5% d'aigua
MAX_RAIN_WATER_GAIN = 100.0  # màxim possible (omple el test)

SOLAR_BASE_WM2 = 200  # W/m² "normals" que ja estan inclosos a BASE_WATER_LOSS
SOLAR_WM2_TO_WATER_LOSS = 0.008  # cada W/m² extra = +0.008% de pèrdua/hora
MAX_SOLAR_EXTRA_LOSS = 10.0  # màxim de 10% extra/hora

HUMIDITY_OPTIMAL = 60.0  # % d'humitat "normal"
HUMIDITY_TO_WATER_LOSS = 0.04  # cada % per sota de l'òptim = +0.04% de pèrdua/hora
MAX_HUMIDITY_EXTRA_LOSS = 3.0  # cap a un màxim de 3% extra/hora

TEMP_DEGREE_TO_HEALTH_LOSS = 0.15  # cada grau fora del rang = -0.15% salut/hora
MAX_TEMP_HEALTH_LOSS = 8.0  # cap a un màxim de 8%/hora

WIND_SAFE_MS = 5.0  # m/s per sota dels quals el vent no fa mal
WIND_MS_TO_HEALTH_LOSS = 0.2  # cada m/s per sobre del segur = -0.2% salut/hora
MAX_WIND_HEALTH_LOSS = 5.0  # cap a un màxim de 5%/hora

DEHYDRATION_THRESHOLD = 20.0  # % d'aigua per sota del qual la planta pateix
DEHYDRATION_TO_HEALTH = 0.25  # cada % per sota = -0.25% salut/hora
MAX_DEHYDRATION_HEALTH_LOSS = 5.0

HEALTH_RECOVERY_PER_HOUR = 1.0  # % salut recuperada/hora en bones condicions

MIN_HEALTH_TO_GROW = 30.0  # % salut mínim per avançar de fase

HOURS_PER_PHASE = {
    GrowthState.SEED: 24,
    GrowthState.GERMINATION: 48,
    GrowthState.GROWTH: 96,
    GrowthState.MATURE: 120,
    GrowthState.FLOWERING: None,
    GrowthState.DEAD: None,
}

PHASE_ORDER = [
    GrowthState.SEED,
    GrowthState.GERMINATION,
    GrowthState.GROWTH,
    GrowthState.MATURE,
    GrowthState.FLOWERING,
]


def simulate_plant(plant_in_garden: PlantInGarden, station: Station) -> PlantInGarden:
    if plant_in_garden.growthPhase == GrowthState.DEAD:
        return plant_in_garden

    # troba interval de temps que no s'ha simulat
    now = timezone.now()
    last_simulated = plant_in_garden.lastSimulatedAt
    if last_simulated.tzinfo is None:
        last_simulated = timezone.make_aware(last_simulated)

    if (now - last_simulated).total_seconds() < 600:
        return plant_in_garden

    # agafa meteorologia de l'interval
    readings = list(
        WeatherReading.objects.filter(
            station=station, timestamp__gte=last_simulated, timestamp__lte=now
        ).order_by("timestamp")
    )
    if not readings:
        return plant_in_garden

    # actualitza planta per cada interval de temps
    for i, reading in enumerate(readings):
        if plant_in_garden.growthPhase == GrowthState.DEAD:
            break
        if i + 1 < len(readings):
            interval_hours = (
                readings[i + 1].timestamp - reading.timestamp
            ).total_seconds() / 3600.0
        else:
            interval_hours = (now - reading.timestamp).total_seconds() / 3600.0

        # interval_hours = min(max(interval_hours, 0.0), 2.0)
        if interval_hours == 0:
            continue

        plant_in_garden = _apply_reading(plant_in_garden, reading, interval_hours)

    if plant_in_garden.growthPhase != GrowthState.DEAD:
        plant_in_garden.lastSimulatedAt = now

    return plant_in_garden


def _apply_reading(
    pig: PlantInGarden,
    reading: WeatherReading,
    interval_hours: float,
) -> PlantInGarden:
    # Si variable no disponible valors optims
    temperature = reading.temperature if reading.temperature is not None else 20.0
    precipitation = reading.precipitation if reading.precipitation is not None else 0.0
    solar = (
        reading.solarIrradiance
        if reading.solarIrradiance is not None
        else SOLAR_BASE_WM2
    )
    wind = reading.windSpeed if reading.windSpeed is not None else 0.0
    humidity = (
        reading.relativeHumidity
        if reading.relativeHumidity is not None
        else HUMIDITY_OPTIMAL
    )

    ### Aigua
    if precipitation >= RAIN_THRESHOLD_MM:
        net_water_per_hour = min(
            precipitation * RAIN_MM_TO_WATER_PERCENT,
            MAX_RAIN_WATER_GAIN,
        )
    else:
        loss = BASE_WATER_LOSS_PER_HOUR

        if solar > SOLAR_BASE_WM2:
            solar_extra = min(
                (solar - SOLAR_BASE_WM2) * SOLAR_WM2_TO_WATER_LOSS,
                MAX_SOLAR_EXTRA_LOSS,
            )
            loss += solar_extra

        if humidity < HUMIDITY_OPTIMAL:
            humidity_extra = min(
                (HUMIDITY_OPTIMAL - humidity) * HUMIDITY_TO_WATER_LOSS,
                MAX_HUMIDITY_EXTRA_LOSS,
            )
            loss += humidity_extra

        net_water_per_hour = -loss

    new_water = _clamp(pig.waterLevel + net_water_per_hour * interval_hours, 0.0, 100.0)

    ### Salut
    health_delta_per_hour = 0.0

    min_temp = pig.plant.minTemperature
    max_temp = pig.plant.maxTemperature

    if temperature < min_temp:
        degrees_out = min_temp - temperature
        health_delta_per_hour -= min(
            degrees_out * TEMP_DEGREE_TO_HEALTH_LOSS,
            MAX_TEMP_HEALTH_LOSS,
        )
    elif temperature > max_temp:
        degrees_out = temperature - max_temp
        health_delta_per_hour -= min(
            degrees_out * TEMP_DEGREE_TO_HEALTH_LOSS,
            MAX_TEMP_HEALTH_LOSS,
        )

    if wind > WIND_SAFE_MS:
        health_delta_per_hour -= min(
            (wind - WIND_SAFE_MS) * WIND_MS_TO_HEALTH_LOSS,
            MAX_WIND_HEALTH_LOSS,
        )

    avg_water = (
        pig.waterLevel + new_water
    ) / 2.0  # nivell mitjà de l'aigua durant l'interval
    if avg_water < DEHYDRATION_THRESHOLD:
        health_delta_per_hour -= min(
            (DEHYDRATION_THRESHOLD - avg_water) * DEHYDRATION_TO_HEALTH,
            MAX_DEHYDRATION_HEALTH_LOSS,
        )

    # Recuperació si tot va bé
    if health_delta_per_hour == 0.0:
        health_delta_per_hour = HEALTH_RECOVERY_PER_HOUR

    new_health = _clamp(
        pig.healthLevel + health_delta_per_hour * interval_hours, 0.0, 100.0
    )

    # Mort
    if new_health <= 0.0:
        pig.growthPhase = GrowthState.DEAD
        pig.healthLevel = 0.0
        pig.waterLevel = new_water
        pig.lastSimulatedAt = reading.timestamp
        return pig

    # Actualitzar vives
    pig.waterLevel = new_water
    pig.healthLevel = new_health
    pig.growthPhase = _recalculate_phase(pig, new_health, reading.timestamp)

    return pig


def _recalculate_phase(pig: PlantInGarden, health: float, current_time) -> str:
    current_phase = pig.growthPhase

    if current_phase in (GrowthState.FLOWERING, GrowthState.DEAD):
        return current_phase
    if health < MIN_HEALTH_TO_GROW:
        return current_phase

    planted_at = pig.plantedAt
    if planted_at.tzinfo is None and current_time.tzinfo is not None:
        planted_at = timezone.make_aware(planted_at)

    total_hours = (current_time - planted_at).total_seconds() / 3600.0
    accumulated = 0.0
    target_phase = current_phase

    for phase in PHASE_ORDER:
        duration = HOURS_PER_PHASE.get(phase)
        if duration is None:
            break
        accumulated += duration
        if total_hours >= accumulated:
            nxt = _next_phase(phase, pig.plant.canFlower)
            if nxt:
                target_phase = nxt
        else:
            break

    return target_phase


def _next_phase(phase: str, can_flower: bool) -> str | None:
    try:
        idx = PHASE_ORDER.index(phase)
    except ValueError:
        return None
    nxt_idx = idx + 1
    if nxt_idx >= len(PHASE_ORDER):
        return None
    nxt = PHASE_ORDER[nxt_idx]
    if nxt == GrowthState.FLOWERING and not can_flower:
        return None
    return nxt


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
