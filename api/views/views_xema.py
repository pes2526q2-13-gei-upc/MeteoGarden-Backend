import os

import requests
from dotenv import load_dotenv
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Station, WeatherReading
from ..xema_sync import ensure_station_synced

load_dotenv()

XEMA_METEO_TOKEN = os.getenv("XEMA_METEO_TOKEN")


# GET {BASE_URL}/api/weather/current/?stationCode=<codi_estació>
# GET {BASE_URL}/api/weather/current/?stationName=<nom_estació>
@api_view(["GET"])
@permission_classes([AllowAny])
def current_weather(request):
    station_code = request.GET.get("stationCode")
    station_name = request.GET.get("stationName")

    if not station_code and not station_name:
        return Response(
            {"error": "stationCode or stationName is required"},
            status=400,
        )

    # Trobem la estació en la nostra BD
    if station_code:
        station = Station.objects.filter(stationCode=station_code).first()
    else:
        station = Station.objects.filter(station__iexact=station_name).first()
    if not station:
        return Response({"error": "Station not found"}, status=404)

    ensure_station_synced(station)

    # Agafem la lectura més recent
    latest = (
        WeatherReading.objects.filter(station=station).order_by("-timestamp").first()
    )

    if not latest:
        return Response(
            {"error": "No weather data available for this station"},
            status=503,
        )

    # Retornem els valors
    return Response(
        {
            "stationName": station.station,
            "temperature": latest.temperature,
            "precipitation": latest.precipitation,
            "wind": latest.windSpeed,
            # "solarIrradiance": latest.solarIrradiance,
            # "relativeHumidity": latest.relativeHumidity,
        }
    )


# GET {BASE_URL}/api/stations/
@api_view(["GET"])
@permission_classes([AllowAny])
def get_stations(request):
    # Si ja tenim estacions a la BD, les servim directament
    stations_qs = Station.objects.all().order_by("station")
    if stations_qs.exists():
        return Response(
            [{"name": s.station, "code": s.stationCode} for s in stations_qs]
        )

    # Primera vegada: carreguem de la XEMA i guardem a la BD
    try:
        url = (
            "https://analisi.transparenciacatalunya.cat/resource/yqwd-vj5e.json"
            "?$select=nom_estacio,codi_estacio"
            "&$where=nom_estat_ema='Operativa'"
            "&$order=nom_estacio"
        )
        response = requests.get(url, timeout=10).json()

        if not isinstance(response, list):
            return Response(
                {"error": "Invalid response from XEMA", "data": response}, status=500
            )

        stations = []
        for row in response:
            name = row.get("nom_estacio", "")
            code = row.get("codi_estacio", "")
            # aquest potser estaria bé treure'l del model
            city = row.get("municipi", name)

            # Guardem a la BD per a futures consultes
            Station.objects.get_or_create(
                stationCode=code,
                defaults={
                    "station": name,
                    "city": city,
                    "solarIrradiance": 0,
                    "temperature": 0.0,
                    "windSpeed": 0.0,
                    "relativeHumidity": 0.0,
                    "precipitation": 0.0,
                },
            )
            stations.append({"name": name, "code": code})

        return Response(stations)

    except Exception as e:
        return Response({"error": str(e)}, status=500)
