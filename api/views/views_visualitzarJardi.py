from datetime import timedelta

from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from api.models import (
    Garden,
    GrowthState,
    Inventory,
    MissionAction,
    MissionState,
    Plant,
    Pot,
    Station,
    User,
    UserMission,
)
from api.plant_simulation import simulate_plant
from api.serializer import (
    InventoryProductSerializer,
    InventorySeedSerializer,
    PotSerializer,
)
from api.services.xema_sync import ensure_station_synced


def update_water_missions(user, plant):
    user_missions = UserMission.objects.filter(
        user=user,
        missionState=MissionState.IN_PROGRESS,
        mission__action=MissionAction.WATER,
    ).select_related("mission", "mission__plant")

    for user_mission in user_missions:
        mission = user_mission.mission

        if mission.plant is None or mission.plant == plant:
            user_mission.current += 1

            if mission.goal <= user_mission.current:
                user_mission.missionState = MissionState.COMPLETED

            user_mission.save()


def _sync_user_station(user: User) -> Station | None:
    station = Station.objects.filter(stationCode=user.stationCode).first()
    if station:
        ensure_station_synced(station)
    return station


def _simulate_garden(garden: Garden) -> None:
    station = _sync_user_station(garden.user)
    if not station:
        return

    pigs = (
        garden.pot_set.exclude(plantingarden__isnull=True)
        .exclude(plantingarden__growthPhase=GrowthState.DEAD)
        .select_related("plantingarden__plant")
    )
    for pot in pigs:
        pig = pot.plantingarden
        updated = simulate_plant(pig, station)
        updated.save()


def garden_plants(request, username, garden_name):
    garden = get_object_or_404(
        Garden.objects.select_related("user"),
        user__username=username,
        name=garden_name,
    )

    _simulate_garden(garden)

    pots = (
        Pot.objects.filter(garden=garden)
        .order_by("number")
        .select_related("plantingarden", "plantingarden__plant")
    )
    serializer = PotSerializer(pots, many=True)
    return JsonResponse(serializer.data, safe=False)


def user_gardens(request, username):
    user = get_object_or_404(User, username=username)

    gardens = Garden.objects.filter(user=user).order_by("name")

    data = [
        {
            "name": garden.name,
        }
        for garden in gardens
    ]

    return JsonResponse(data, safe=False)


def plant_status(request, username, garden_name, pot_number):
    garden = get_object_or_404(Garden, user__username=username, name=garden_name)
    pot = get_object_or_404(Pot, garden=garden, number=pot_number)

    planting = getattr(pot, "plantingarden", None)

    if planting and planting.growthPhase != GrowthState.DEAD:
        station = _sync_user_station(garden.user)
        if station:
            planting = simulate_plant(planting, station)
            planting.save()

    serializer = PotSerializer(pot)
    return JsonResponse(serializer.data)


@csrf_exempt
def water_plant(request, username, garden_name, pot_number):
    if request.method != "PATCH":
        return HttpResponseNotAllowed(["PATCH"])

    garden = get_object_or_404(
        Garden,
        user__username=username,
        name=garden_name,
    )

    pot = get_object_or_404(
        Pot,
        garden=garden,
        number=pot_number,
    )

    planting = getattr(pot, "plantingarden", None)

    if planting is None:
        return JsonResponse(
            {"error": "There is no plant in this pot."},
            status=404,
        )

    # ns si actualitzar aqui la planta o no abans de regar
    # if planting.growthPhase != GrowthState.DEAD:
    #    station = _sync_user_station(garden.user)
    #    if station:
    #        planting = simulate_plant(planting, station)

    planting.waterLevel = 100.0
    now = timezone.now()

    if now - planting.lastWateredAt < timedelta(hours=10):
        remaining = timedelta(hours=10) - (now - planting.lastWateredAt)
        total_seconds = int(remaining.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        return JsonResponse(
            {
                "error": "Plant was watered recently.",
                "message": (
                    f"You must wait {hours}h {minutes}m before watering again."
                ),
            },
            status=400,
        )

    planting.waterLevel = min(100.0, planting.waterLevel + 50.0)
    planting.healthLevel = min(100.0, planting.healthLevel + 5.0)
    planting.lastWateredAt = now
    planting.save()

    user = get_object_or_404(User, username=username)
    plant = Plant.objects.get(scientificName=planting.plant.scientificName)
    update_water_missions(user, plant)

    data = {
        "message": "Plant watered successfully.",
        "pot_number": pot.number,
        "plant": {
            "scientific_name": planting.plant.scientificName,
            "common_name": planting.plant.commonName,
        },
        "water_level": planting.waterLevel,
        "health_level": planting.healthLevel,
        "last_watered_at": planting.lastWateredAt.isoformat(),
    }

    return JsonResponse(data, status=200)


# def user_seeds(request, username):
#     if request.method != "GET":
#         return HttpResponseNotAllowed(["GET"])
#
#     user = get_object_or_404(User, username=username)
#
#     inventory, _ = Inventory.objects.get_or_create(user=user)
#
#     seeds_data = [
#         {"scientificName": seed, "amount": amount}
#         for seed, amount in inventory.seeds.items()
#     ]
#
#     serializer = InventorySeedSerializer(seeds_data, many=True)
#     return Response(serializer.data)
def user_seeds(request, username):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    user = get_object_or_404(User, username=username)
    inventory, _ = Inventory.objects.get_or_create(user=user)

    seeds_data = [
        {"scientificName": seed, "amount": amount}
        for seed, amount in inventory.seeds.items()
    ]

    serializer = InventorySeedSerializer(seeds_data, many=True)
    return JsonResponse(serializer.data, safe=False)


def user_products(request, username):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    user = get_object_or_404(User, username=username)
    inventory, _ = Inventory.objects.get_or_create(user=user)

    products_data = [
        {"productName": product, "amount": amount}
        for product, amount in sorted(inventory.products.items())
    ]

    serializer = InventoryProductSerializer(products_data, many=True)
    return JsonResponse(serializer.data, safe=False)
