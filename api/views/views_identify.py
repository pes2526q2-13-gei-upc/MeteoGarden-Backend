# from django.shortcuts import render
import os

import requests
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import (
    AlbumEntry,
    Image,
    Inventory,
    MissionAction,
    MissionState,
    Plant,
    User,
    UserMission,
)
from .views_info import getInfoPlant

PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"
ALLOWED_ORGANS = {"leaf", "flower"}


def updatePhotoMissions(user, plant):
    allUserMissions = UserMission.objects.filter(
        user=user, missionState=MissionState.IN_PROGRESS
    )
    for mission in allUserMissions:
        if mission.mission.action == MissionAction.PHOTO:
            if mission.mission.plant is None or mission.mission.plant == plant:
                mission.current += 1
                if mission.mission.goal <= mission.current:
                    mission.missionState = MissionState.COMPLETED
                mission.save()


@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def identifyPlant(request):

    username = request.data.get("username")
    file_obj = request.FILES.get("image")
    organ = request.data.get("organ")

    if not username:
        return Response({"error": "Username required"}, status=400)

    if not file_obj:
        return Response({"image": "Image file is required."}, status=400)

    if organ not in ALLOWED_ORGANS:
        return Response(
            {"organs": f"Invalid value. Must be one of: {sorted(ALLOWED_ORGANS)}"},
            status=400,
        )

    api_key = os.getenv("PLANTNET_API_KEY")
    if not api_key:
        return Response({"detail": "PLANTNET_API_KEY is not configured."}, status=500)

    files = {
        "images": (
            file_obj.name,
            file_obj,
            file_obj.content_type or "application/octet-stream",
        )
    }

    r = requests.post(
        f"{PLANTNET_URL}?api-key={api_key}",
        files=files,
        data={"organs": organ},
        timeout=30,
    )

    if r.status_code != 200:
        return Response(
            {
                "detail": "PlantNet identification failed.",
                "status_code": r.status_code,
                "body": r.text[:500],
            },
            status=502,
        )

    payload = r.json()

    results = payload.get("results") or []
    if not results:
        return Response({"detail": "No identification results."}, status=422)

    best = results[0]
    species = best.get("species") or {}
    scientificName = species.get("scientificNameWithoutAuthor") or species.get(
        "scientificName"
    )

    if not scientificName:
        return Response(
            {"detail": "PlantNet response missing scientific name."}, status=422
        )

    try:
        uploader = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"username": "User not found."}, status=404)

    getInfoPlant(scientificName, uploader.language)
    plant = Plant.objects.get(scientificName=scientificName)

    if plant.commonName is None:
        common_names = species.get("commonNames", [])

        family_data = species.get("family")
        family_name = (
            family_data.get("scientificNameWithoutAuthor") if family_data else None
        )

        if common_names:
            plant.commonName = common_names[0]
        if family_name:
            plant.family = family_name
        plant.save()

    img = Image.objects.create(
        uploader=uploader,
        url=file_obj,
        plant=plant,
    )

    AlbumEntry.objects.get_or_create(
        user=uploader,
        plant=plant,
        defaults={
            "description": plant.description or "",
        },
    )

    inventory, _ = Inventory.objects.get_or_create(user=uploader)
    Inventory.addSeed(inventory, scientificName, 2)

    updatePhotoMissions(uploader, plant)

    return Response(
        {
            "plant": {
                "scientificName": plant.scientificName,
                "commonName": plant.commonName,
                "family": plant.family,
            },
            "image": {
                "id": img.id,
                "url": img.url.url if img.url else None,
                "width": img.width,
                "height": img.height,
            },
            "plantnet": {
                "score": best.get("score"),
            },
        },
        status=201,
    )
