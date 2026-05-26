import json

from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from ..models import (
    Garden,
    GrowthState,
    Inventory,
    MissionAction,
    MissionState,
    Plant,
    PlantInGarden,
    Pot,
    User,
    UserMission,
)
from .views_translate import translate_text


def update_plant_missions(user, plant):
    # Obtenim les missions
    missions = UserMission.objects.filter(
        user=user,
        missionState=MissionState.IN_PROGRESS,
        mission__action=MissionAction.PLANT,
    )
    for user_mission in missions:
        mission = user_mission.mission

        if mission.plant is None or mission.plant == plant:
            user_mission.current += 1

            if mission.goal <= user_mission.current:
                user_mission.missionState = MissionState.COMPLETED

            user_mission.save()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def plant_seed(request, username, garden_name, pot_number):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = get_object_or_404(User, username=username)
    lang = user.language

    garden = get_object_or_404(
        Garden,
        user=user,
        name=garden_name,
    )

    pot = get_object_or_404(
        Pot,
        garden=garden,
        number=pot_number,
    )

    if getattr(pot, "plantingarden", None) is not None:
        return JsonResponse(
            {"error": translate_text("This pot is already occupied.", lang)},
            status=400,
        )

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": translate_text("Invalid JSON body.", lang)},
            status=400,
        )

    scientific_name = body.get("scientificName")

    if not scientific_name:
        return JsonResponse(
            {"error": translate_text("The field 'scientificName' is required.", lang)},
            status=400,
        )

    plant = get_object_or_404(Plant, scientificName=scientific_name)
    inventory, _ = Inventory.objects.get_or_create(user=user)

    current_amount = inventory.seeds.get(scientific_name, 0)

    if current_amount <= 0:
        return JsonResponse(
            {
                "error": translate_text(
                    "The user does not have this seed in the inventory.", lang
                )
            },
            status=400,
        )

    inventory.seeds[scientific_name] = current_amount - 1
    if inventory.seeds[scientific_name] == 0:
        del inventory.seeds[scientific_name]
    inventory.save()

    planting = PlantInGarden.objects.create(
        pot=pot,
        plant=plant,
        plantedAt=timezone.now(),
        growthPhase=GrowthState.SEED,
        healthLevel=100.0,
        waterLevel=100.0,
        lastWateredAt=timezone.now(),
    )

    update_plant_missions(user, plant)

    data = {
        "message": translate_text("Plant planted successfully.", lang),
        "pot_number": pot.number,
        "plant": {
            "scientificName": planting.plant.scientificName,
            "commonName": planting.plant.commonName,
        },
        "growthPhase": planting.growthPhase,
        "healthLevel": planting.healthLevel,
        "waterLevel": planting.waterLevel,
        "plantedAt": planting.plantedAt.isoformat(),
        "remainingSeeds": inventory.seeds.get(scientific_name, 0),
    }

    return JsonResponse(data, status=201)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_plant(request, username, garden_name, pot_number):
    user = get_object_or_404(User, username=username)
    lang = user.language

    garden = get_object_or_404(
        Garden,
        user=user,
        name=garden_name,
    )
    if garden is None:
        return JsonResponse(
            {"error": translate_text("There is no garden with this name.", lang)},
            status=404,
        )
    pot = get_object_or_404(
        Pot,
        garden=garden,
        number=pot_number,
    )

    planting = getattr(pot, "plantingarden", None)

    if planting is None:
        return JsonResponse(
            {"error": translate_text("There is no plant in this pot.", lang)},
            status=404,
        )

    plant_name = planting.plant.scientificName
    pot_num = pot.number

    planting.delete()  # tu delete() ya pone occupied=False en la maceta

    data = {
        "message": translate_text("Plant deleted successfully.", lang),
        "pot_number": pot_num,
        "deletedPlant": plant_name,
        "occupied": pot.occupied,
    }

    return JsonResponse(data, status=200)
