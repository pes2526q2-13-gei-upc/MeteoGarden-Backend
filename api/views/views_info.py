# from django.shortcuts import render
import os

import requests
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Image, Plant
from .views_image import createPlantImages

TEMPS_RANGES = [
    (-51.1, 20),
    (-45.6, 22),
    (-40, 24),
    (-34.4, 25),
    (-28.9, 26),
    (-23.3, 28),
    (-17.8, 30),
    (-12.2, 33),
    (-6.7, 36),
    (-1.1, 40),
    (4.4, 45),
    (10, 50),
    (15.6, 55),
]


def translate(text: str | None, lang: str) -> str | None:
    if not text:
        return None

    api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    if not api_key:
        # if there's no key, returns the original text
        return text

    url = "https://translation.googleapis.com/language/translate/v2"
    params = {"q": text, "target": lang, "format": "text", "key": api_key}

    response = requests.post(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["data"]["translations"][0]["translatedText"]


def getTemperature(zone_min, zone_max) -> tuple[float | None, float | None]:
    if zone_min is None or zone_max is None:
        return None, None
    zone_min = int(str(zone_min))
    zone_max = int(str(zone_max))
    return float(TEMPS_RANGES[zone_min - 1][0]), float(TEMPS_RANGES[zone_max - 1][1])


def getPlantInfoFromAPI(scientific_name: str) -> dict | None:
    key = os.getenv("PERENUAL_API_KEY")
    if not key:
        raise RuntimeError("There's no API key for Perenual.")

    url = "https://perenual.com/api/species-list?"
    params = {"key": os.getenv("PERENUAL_API_KEY"), "q": scientific_name}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if not data.get("data"):
        return None

    id = data["data"][0]["id"]
    url_details = "https://perenual.com/api/v2/species/details/" + str(id)
    params_details = {"key": os.getenv("PERENUAL_API_KEY")}
    response_details = requests.get(url_details, params=params_details)
    response_details.raise_for_status()
    return response_details.json()


def filterInfo(details: dict, lang: str) -> dict | None:
    if details is None:
        return None

    sci_list = details.get("scientific_name") or []
    sci = sci_list[0] if sci_list else None

    hard = details.get("hardiness") or {}
    minTemperature, maxTemperature = getTemperature(hard.get("min"), hard.get("max"))

    description = details.get("description")

    info = {
        "scientificName": sci,
        "commonName": details.get("common_name").capitalize(),
        "family": details.get("family"),
        "canFlower": details.get("flowers"),
        "minTemperature": minTemperature,
        "maxTemperature": maxTemperature,
        "description": description,
    }

    saveOrUpdatePlant(info)
    if lang != "en" and lang != "EN":
        info.update(
            {
                "commonName": translate(info["commonName"], lang),
                "description": translate(description, lang),
            }
        )

    return info


@transaction.atomic
def saveOrUpdatePlant(details: dict):
    Plant.objects.update_or_create(
        scientificName=details.get("scientificName"),
        defaults={
            "commonName": details.get("commonName"),
            "family": details.get("family"),
            "canFlower": details.get("canFlower"),
            "minTemperature": details.get("minTemperature"),
            "maxTemperature": details.get("maxTemperature"),
            "description": details.get("description"),
        },
    )
    createPlantImages(details.get("scientificName"))


def getPlant(scientific_name: str) -> Plant | None:
    return Plant.objects.filter(scientificName=scientific_name).first()


def getInfoPlant(scientific_name: str, lang: str) -> dict | None:
    plant = Plant.objects.filter(scientificName=scientific_name).first()

    if plant is None:
        details = getPlantInfoFromAPI(scientific_name)
        return filterInfo(details, lang)

    else:
        desc = plant.description
        commonName = plant.commonName
        if lang != "en" and lang != "EN":
            print(lang)
            desc = translate(desc, lang)
            print("traduir")
            commonName = translate(commonName, lang)
        print(scientific_name)
        image = Image.objects.filter(plant=scientific_name).first()
        print(image.url)

        return {
            "scientificName": plant.scientificName,
            "commonName": commonName.capitalize(),
            "family": plant.family,
            "canFlower": plant.canFlower,
            "minTemperature": plant.minTemperature,
            "maxTemperature": plant.maxTemperature,
            "description": desc,
        }


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def importPlant(request):
    if request.method == "POST":
        data_source = request.data
    else:
        data_source = request.query_params

    sc_name_input = data_source.get("scientificName")
    url_param = data_source.get("url")
    lang = data_source.get("lang")

    scientific_name = None
    if sc_name_input:
        scientific_name = sc_name_input

    elif url_param:
        image = Image.objects.filter(url=url_param).first()
        if image:
            scientific_name = image.plant_id
        else:
            return Response({"error": "Plant not found with that url"}, status=404)

    if not scientific_name:
        return Response({"error": "scientificName is required"}, status=400)

    try:
        plant = getInfoPlant(scientific_name, lang)
        return Response(plant, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
