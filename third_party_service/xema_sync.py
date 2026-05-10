import logging
import os
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

import requests
from django.utils import timezone
from dotenv import load_dotenv

from .models import Station, WeatherReading

load_dotenv()

logger = logging.getLogger(__name__)

XEMA_METEO_TOKEN = os.getenv("XEMA_METEO_TOKEN")
XEMA_URL = "https://analisi.transparenciacatalunya.cat/resource/nzvn-apee.json"

DIRECT_VARIABLES = {
    "32": "temperature",  # Temperatura (ºC) — UNIVERSAL
    "35": "precipitation",  # Precipitació acumulada (mm) — UNIVERSAL
    "36": "solarIrradiance",  # Irradiància solar (W/m^2)
}


ALL_VARIABLE_CODES = list(DIRECT_VARIABLES.keys())

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
    def parse_row(row):
        ts_str = row.get("data_lectura", "")
        var_code = row.get("codi_variable", "")
        val = row.get("valor_lectura")
        if not ts_str or var_code not in ALL_VARIABLE_CODES or val is None:
            return None, None, None
        try:
            float_val = float(val)
        except ValueError:
            return None, None, None
        return ts_str, var_code, float_val

    def parse_timestamp(ts_str):
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=dt_timezone.utc)
            return ts
        except ValueError:
            return None

    def request_rows(url):
        try:
            response = requests.get(
                url,
                headers={"X-App-Token": XEMA_METEO_TOKEN},
                timeout=15,
            )
            data = response.json()
            if not isinstance(data, list):
                logger.error(f"[XEMA sync] Resposta inesperada: {data}")
                return []
            return data
        except Exception as e:
            logger.error(
                f"[XEMA sync] Error consultant l'estació {station.stationCode}: {e}"
            )
            return []

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

    rows = request_rows(url)
    if not rows:
        return 0

    by_timestamp: dict[str, dict[str, float]] = {}
    for row in rows:
        ts_str, var_code, float_val = parse_row(row)
        if ts_str:
            by_timestamp.setdefault(ts_str, {})[var_code] = float_val

    saved = 0
    for ts_str, codes in by_timestamp.items():
        ts = parse_timestamp(ts_str)
        if not ts:
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
