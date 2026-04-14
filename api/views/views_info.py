# from django.shortcuts import render
import os

import requests
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Plant
from .views_image import createPlantImages
from .views_translate import translate_text

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

DEFAULT_MIN_TEMPERATURE = 2
DEFAULT_MAX_TEMPERATURE = 30


def getTemperature(zone_min, zone_max) -> tuple[float | None, float | None]:
    if zone_min is None or zone_max is None:
        return None, None
    zone_min = int(str(zone_min))
    zone_max = int(str(zone_max))
    return float(TEMPS_RANGES[zone_min - 1][0]), float(TEMPS_RANGES[zone_max - 1][1])


def inferCanFlowerFromGBIF(scientific_name: str) -> bool | None:
    try:
        response = requests.get(
            "https://api.gbif.org/v1/species/match",
            params={"name": scientific_name, "verbose": True},
            timeout=5,
        )
        data = response.json()

        clazz = data.get("class", "").lower()
        phylum = data.get("phylum", "").lower()

        FLOWERING_CLASSES = {"magnoliopsida", "liliopsida", "polypodiopsida"}
        NON_FLOWERING_PHYLA = {"pinophyta", "cycadophyta", "ginkgophyta"}

        if clazz in FLOWERING_CLASSES:
            return True
        if phylum in NON_FLOWERING_PHYLA:
            return False
        return None
    except Exception:
        return None


def getInfoFromWikipedia(scientific_name: str) -> dict:
    try:
        response = requests.get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + scientific_name.replace(" ", "_"),
            headers={
                "User-Agent": "MeteoGarden/1.0 https://github.com/pes2526q2-13-gei-upc/MeteoGarden-Backend"
            },
            timeout=5,
        )

        if response.status_code != 200:
            return {"canFlower": None, "description": None}

        extract = response.json().get("extract", "")
        extract_lower = extract.lower()

        if "flowering plant" in extract or "angiosperm" in extract_lower:
            can_flower = True
        elif (
            "conifer" in extract
            or "gymnosperm" in extract_lower
            or "fern" in extract_lower
        ):
            can_flower = False
        else:
            can_flower = inferCanFlowerFromGBIF(scientific_name)

        return {
            "canFlower": can_flower,
            "description": extract.split("\n")[0].strip("\"'") or None,
        }

    except Exception:
        return {"canFlower": None, "description": None}


def resolveScientificName(scientific_name: str) -> str:
    try:
        response = requests.get(
            "https://api.gbif.org/v1/species/match",
            params={"name": scientific_name, "verbose": True},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("synonym") and data.get("species"):
            return data["species"]
        return data.get("species", scientific_name)
    except Exception:
        return scientific_name


def getPlantInfoFromAPI(scientific_name: str) -> dict | None:
    key = os.getenv("PERENUAL_API_KEY")
    if not key:
        raise RuntimeError("There's no API key for Perenual.")

    resolved_name = resolveScientificName(scientific_name)

    try:
        url = "https://perenual.com/api/species-list?"
        params = {"key": os.getenv("PERENUAL_API_KEY"), "q": resolved_name}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("data") and len(resolved_name.split()) > 2:
            short_name = " ".join(resolved_name.split()[:2])
            params["q"] = short_name
            response = requests.get(url, params=params)
            data = response.json()

        if not data.get("data"):
            return None

        id = data["data"][0]["id"]
        url_details = "https://perenual.com/api/v2/species/details/" + str(id)
        params_details = {"key": os.getenv("PERENUAL_API_KEY")}
        response_details = requests.get(url_details, params=params_details)
        if response_details.status_code == 426:
            return None
        response_details.raise_for_status()
        return response_details.json()

    except Exception:
        return None


def filterInfo(scientific_name: str, details: dict, lang: str) -> dict | None:
    if details is None:
        info_wiki = getInfoFromWikipedia(scientific_name)
        info = {
            "scientificName": scientific_name,
            "commonName": None,
            "family": None,
            "canFlower": info_wiki.get("canFlower"),
            "minTemperature": DEFAULT_MIN_TEMPERATURE,
            "maxTemperature": DEFAULT_MAX_TEMPERATURE,
            "description": info_wiki.get("description"),
        }

    else:
        hard = details.get("hardiness") or {}
        minTemperature, maxTemperature = getTemperature(
            hard.get("min"), hard.get("max")
        )

        description = details.get("description")

        info = {
            "scientificName": scientific_name,
            "commonName": details.get("common_name").capitalize(),
            "family": details.get("family"),
            "canFlower": details.get("flowers"),
            "minTemperature": minTemperature,
            "maxTemperature": maxTemperature,
            "description": description,
        }

    saveOrUpdatePlant(info)
    if lang not in ("en", "EN") and details is not None:
        info.update(
            {
                "commonName": translate_text(info["commonName"], lang),
                "description": translate_text(info["description"], lang),
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
        return filterInfo(scientific_name, details, lang)

    else:
        desc = plant.description
        commonName = plant.commonName
        if lang != "en" and lang != "EN":
            desc = translate_text(desc, lang)
            if commonName is not None:
                commonName = translate_text(commonName, lang)

        return {
            "scientificName": plant.scientificName,
            "commonName": commonName,
            "family": plant.family,
            "canFlower": plant.canFlower,
            "minTemperature": plant.minTemperature,
            "maxTemperature": plant.maxTemperature,
            "description": desc,
        }


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def importPlant(request):
    if request.method == "GET":
        scientific_name = request.query_params.get("scientificName")
        lang = request.query_params.get("lang")
    else:
        scientific_name = request.data.get("scientificName")
        lang = request.data.get("lang")

    if not scientific_name:
        return Response({"error": "scientificName is required"}, status=400)

    try:
        plant = getInfoPlant(scientific_name, lang)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

    if plant is None:
        return Response({"error": "Plant not found"}, status=404)

    return Response(plant, status=200)
