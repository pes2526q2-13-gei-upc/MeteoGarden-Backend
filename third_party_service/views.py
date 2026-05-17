from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Max, Min
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.models import Station, WeatherReading
from api.services.xema_sync import _fetch_and_save, ensure_station_synced
from third_party_service.authentication import ApiKeyAuthentication
from third_party_service.models import ApiKey


message_city = "city is required"


def _get_station_by_city(city: str):
    stations = Station.objects.filter(city__icontains=city)

    if not stations.exists():
        return None

    exact = stations.filter(city__iexact=city).first()
    if exact:
        return exact

    return stations.first()


def _aggregate_day(station, day_start, day_end):
    return WeatherReading.objects.filter(
        station=station, timestamp__gte=day_start, timestamp__lt=day_end
    ).aggregate(Max("temperature"), Min("temperature"))


# GET {BASE_URL}/api/weather/current/?city=<ciutat>
@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([ApiKeyAuthentication])
def current_weather(request):
    city = request.GET.get("city")

    if not city:
        return Response({"error": message_city}, status=400)

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
@permission_classes([IsAuthenticated])
@authentication_classes([ApiKeyAuthentication])
def daily_weather(request):
    city = request.GET.get("city")
    date_str = request.GET.get("date")

    if not city:
        return Response({"error": message_city}, status=400)

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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([ApiKeyAuthentication])
def get_stations_for_city(request):
    city = request.GET.get("city")
    if not city:
        return Response({"error": message_city}, status=400)
    stations = Station.objects.filter(city__icontains=city)
    if not stations.exists():
        return Response({"error": f"No station found for city {city}"}, status=404)

    results = []
    for station in stations:
        results.append(
            {
                "city": station.city,
            }
        )
    return Response({"cities": results})


@api_view(["POST"])
@permission_classes([AllowAny])
def register_and_get_key(request):
    username = request.data.get("username", "").strip()
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "")
    key_name = request.data.get("key_name", "Default API Key").strip()

    if not username or not email or not password:
        return Response(
            {"error": "Username, email i password són obligatoris."}, status=400
        )

    user = get_user_model()

    # 1. Intentem crear l'usuari real
    if user.objects.filter(username=username).exists():
        return Response({"error": "Aquest nom d'usuari ja està agafat."}, status=400)

    try:
        user = user.objects.create_user(
            username=username, email=email, password=password
        )
    except Exception as e:
        return Response({"error": f"Error al crear l'usuari: {str(e)}"}, status=400)

    # 2. Li creem la seva primera API Key automàticament
    _, raw_token = ApiKey.issue_token(name=key_name, created_by=user)

    # 3. Retornem tot de cop
    return Response(
        {
            "message": "Usuari registrat amb èxit!",
            "username": user.username,
            "api_key": raw_token,
            "note": "Guarda bé aquesta clau, no es tornarà a mostrar.",
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_and_generate_key(request):
    username = request.data.get("username")
    password = request.data.get("password")
    key_name = request.data.get("key_name", "Clau de Sessió").strip()

    user = authenticate(username=username, password=password)

    if user is None:
        return Response(
            {"error": "Credencials incorrectes. Torna-ho a provar."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return Response(
            {"error": "Aquest compte està desactivat."},
            status=status.HTTP_403_FORBIDDEN,
        )

    _, raw_token = ApiKey.issue_token(name=key_name, created_by=user)

    return Response(
        {
            "status": "Login correcte",
            "username": user.get_username(),
            "api_key": raw_token,
        },
        status=status.HTTP_200_OK,
    )
