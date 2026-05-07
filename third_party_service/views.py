from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from functools import wraps

from django.db.models import Max, Min
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from third_party_service.models import ApiKey, Station, WeatherReading
from third_party_service.xema_sync import _fetch_and_save, ensure_station_synced


def require_api_key(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        key = request.headers.get("X-API-KEY") or request.GET.get("api_key")
        if not key or len(key) < 16:
            return Response({"error": "Invalid or missing API key"}, status=401)
        prefix = key[:16]
        hashed = ApiKey.hash_token(key)
        try:
            token = ApiKey.objects.get(
                key_prefix=prefix,
                key_hash=hashed,
                revoked_at__isnull=True,
            )
            if not token.is_active:
                return Response({"error": "API key is expired or revoked"}, status=401)
            request.token = token
            if token.created_by:
                request.user = token.created_by
            from django.utils import timezone

            token.last_used_at = timezone.now()
            token.save(update_fields=["last_used_at"])
        except ApiKey.DoesNotExist:
            return Response({"error": "Invalid or missing API key"}, status=401)
        return func(request, *args, **kwargs)

    return wrapper


def _get_station_by_city(city: str):
    stations = Station.objects.filter(city__icontains=city)

    if not stations.exists():
        return None

    # Si hi ha coincidència exacta, la prioritzem
    exact = stations.filter(city__iexact=city).first()
    if exact:
        return exact

    # Si no, retornem la primera coincidència parcial
    return stations.first()


def _aggregate_day(station, day_start, day_end):
    return WeatherReading.objects.filter(
        station=station, timestamp__gte=day_start, timestamp__lt=day_end
    ).aggregate(Max("temperature"), Min("temperature"))


# GET {BASE_URL}/api/weather/current/?city=<ciutat>
@api_view(["GET"])
@permission_classes([AllowAny])
@require_api_key
def current_weather(request):
    city = request.GET.get("city")

    if not city:
        return Response({"error": "city is required"}, status=400)

    station = _get_station_by_city(city)
    if not station:
        return Response({"error": f"No station found for city '{city}'"}, status=404)

    ensure_station_synced(station)

    latest = (
        WeatherReading.objects.filter(station=station).order_by("-timestamp").first()
    )

    if not latest:
        return Response(
            {"error": "No weather data available for this station"},
            status=503,
        )

    return Response(
        {
            "city": station.city,
            "temperature": latest.temperature,
            "precipitation": latest.precipitation,
            "solarIrradiance": latest.solarIrradiance,
        }
    )


# GET {BASE_URL}/api/weather/daily/?city=<ciutat>&date=YYYY-MM-DD
@api_view(["GET"])
@permission_classes([AllowAny])
@require_api_key
def daily_weather(request):
    city = request.GET.get("city")
    date_str = request.GET.get("date")

    if not city:
        return Response({"error": "city is required"}, status=400)

    if not date_str:
        return Response({"error": "date is required (YYYY-MM-DD)"}, status=400)

    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return Response(
            {"error": f"Invalid date format '{date_str}'. Use YYYY-MM-DD."},
            status=400,
        )

    if target_date > date.today():
        return Response({"error": "Cannot query future dates"}, status=400)

    station = _get_station_by_city(city)
    if not station:
        return Response({"error": f"No station found for city '{city}'"}, status=404)

    ensure_station_synced(station)

    day_start = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        tzinfo=dt_timezone.utc,
    )
    day_end = day_start + timedelta(days=1)

    agg = _aggregate_day(station, day_start, day_end)
    temp_max = agg["temperature__max"]
    temp_min = agg["temperature__min"]

    # 3r: si no hi ha lectures locals, consultem XEMA sota demanda
    if temp_max is None:
        _fetch_and_save(station, since=day_start, until=day_end)
        agg = _aggregate_day(station, day_start, day_end)
        temp_max = agg["temperature__max"]
        temp_min = agg["temperature__min"]

    return Response(
        {
            "city": station.city,
            "date": date_str,
            "temperatureMax": temp_max,
            "temperatureMin": temp_min,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])  # o [IsAuthenticated]
def create_api_key(request):
    name = request.data.get("name", "")
    if not name:
        return Response({"error": 'El camp "name" és obligatori.'}, status=400)

    # Si fas servir auth, pots associar la clau a l'usuari autenticat:
    user = request.user if request.user.is_authenticated else None

    # Potser vols comprovar que no existeix ja una key amb el mateix nom:
    if ApiKey.objects.filter(name=name).exists():
        return Response(
            {"error": "Ja existeix una API key amb aquest nom."}, status=400
        )

    key_obj, raw_token = ApiKey.issue_token(name=name, created_by=user)
    return Response(
        {
            "name": name,
            "api_key": raw_token,  # <-- Aquesta és la clau en clar, el client l'ha de guardar!
        }
    )
