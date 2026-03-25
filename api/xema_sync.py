import logging
import os
from datetime import datetime, timedelta

import requests
from django.utils import timezone
from dotenv import load_dotenv

from .models import Station, WeatherReading

load_dotenv()
logger = logging.getLogger(__name__)

XEMA_TOKEN = os.getenv("XEMA_METEO_TOKEN")
XEMA_URL = "https://analisi.transparenciacatalunya.cat/resource/nzvn-apee.json"

DIRECT_VARIABLES = {
    "32": "temperature",  # Temperatura (ºC) — UNIVERSAL
    "35": "precipitation",  # Precipitació acumulada (mm) — UNIVERSAL
    "33": "relativeHumidity",  # Humitat relativa (%) — ALTA cobertura
    "36": "solarIrradiance",  # Irradiància solar global (W/m²) — MITJANA cobertura
}

WIND_CODES_BY_PRIORITY = ["46", "48", "30"]
# 30 = Velocitat del vent a 10 m
# 48 = Velocitat del vent a 6 m
# 46 = Velocitat del vent a 2 m

ALL_VARIABLE_CODES = list(DIRECT_VARIABLES.keys()) + WIND_CODES_BY_PRIORITY

SYNC_INTERVAL_MINUTES = 30
HISTORY_DAYS = 30


# True si s'ha fet una crida a XEMA, false si no calia
def ensure_station_synced(station: Station) -> bool:
    now = timezone.now()

    last_reading = (
        WeatherReading.objects.filter(station=station).order_by("-timestamp").first()
    )

    if last_reading:
        minutes_since_last = (now - last_reading.timestamp).total_seconds() / 60
        if minutes_since_last < SYNC_INTERVAL_MINUTES:
            return False
        # tb les d'1h abans per si s'ha actualitzat tard el XEMA
        since = last_reading.timestamp - timedelta(hours=1)
    else:
        # Primera vegada: agafem les últimes 48h
        since = now - timedelta(hours=48)

    _fetch_and_save(station, since, now)
    _cleanup_old_readings(station)
    return True


def _fetch_and_save(station: Station, since: datetime, until: datetime) -> int:

    fmt = "%Y-%m-%dT%H:%M:%S"
    since_str = since.strftime(fmt)
    until_str = until.strftime(fmt)

    var_codes_str = ",".join(f"'{c}'" for c in ALL_VARIABLE_CODES)

    url = (
        f"{XEMA_URL}"
        f"?$where=codi_estacio='{station.stationCode}'"
        f" AND codi_variable IN ({var_codes_str})"
        f" AND data_lectura between '{since_str}' and '{until_str}'"
        f"&$order=data_lectura ASC"
        f"&$limit=5000"
    )

    try:
        rows = requests.get(
            url,
            headers={"X-App-Token": XEMA_TOKEN},
            timeout=15,
        ).json()
    except Exception as e:
        logger.error(
            f"[XEMA sync] Error consultant l'estació {station.stationCode}: {e}"
        )
        return 0

    if not isinstance(rows, list):
        logger.error(f"[XEMA sync] Resposta inesperada: {rows}")
        return 0

    # Agrupa variables per data { "2026-03-17T10:00:00": {"32": 18.4, "35": 0.0, ...} }
    by_timestamp: dict[str, dict[str, float]] = {}

    for row in rows:
        ts_str = row.get("data_lectura", "")
        var_code = row.get("codi_variable", "")
        val = row.get("valor_lectura")

        if not ts_str or var_code not in ALL_VARIABLE_CODES or val is None:
            continue
        try:
            float_val = float(val)
        except ValueError:
            continue

        if ts_str not in by_timestamp:
            by_timestamp[ts_str] = {}
        by_timestamp[ts_str][var_code] = float_val

    # Guardem a la BD
    saved = 0
    for ts_str, codes in by_timestamp.items():
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        fields = _build_fields(codes)

        _, created = WeatherReading.objects.update_or_create(
            station=station,
            timestamp=ts,
            defaults=fields,
        )
        if created:
            saved += 1

    logger.info(
        f"[XEMA sync] {station.stationCode}: {saved} lectures noves "
        f"({len(rows)} files rebudes)"
    )
    return saved


def _build_fields(codes: dict[str, float]) -> dict:

    fields = {}

    # Variables directes
    for code, field_name in DIRECT_VARIABLES.items():
        if code in codes:
            fields[field_name] = codes[code]

    # Vent amb fallback: agafem el primer codi disponible per ordre de prioritat
    for wind_code in WIND_CODES_BY_PRIORITY:
        if wind_code in codes:
            fields["windSpeed"] = codes[wind_code]
            break
    # Variables que no hi siguin es crearan com a None

    return fields


def _cleanup_old_readings(station: Station) -> None:
    cutoff = timezone.now() - timedelta(days=HISTORY_DAYS)
    deleted, _ = WeatherReading.objects.filter(
        station=station,
        timestamp__lt=cutoff,
    ).delete()
    if deleted:
        logger.debug(
            f"[XEMA sync] {station.stationCode}: {deleted} lectures antigues eliminades."
        )
