import json

from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from ..models import Garden, GrowthState, Inventory, Plant, PlantInGarden, Pot, User


@csrf_exempt
def plant_seed(request, username, garden_name, pot_number):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = get_object_or_404(User, username=username)

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
            {"error": "This pot is already occupied."},
            status=400,
        )

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON body."},
            status=400,
        )

    scientific_name = body.get("scientificName")

    if not scientific_name:
        return JsonResponse(
            {"error": "The field 'scientificName' is required."},
            status=400,
        )

    plant = get_object_or_404(Plant, scientificName=scientific_name)
    inventory, _ = Inventory.objects.get_or_create(user=user)

    current_amount = inventory.seeds.get(scientific_name, 0)

    if current_amount <= 0:
        return JsonResponse(
            {"error": "The user does not have this seed in the inventory."},
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

    data = {
        "message": "Plant planted successfully.",
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
