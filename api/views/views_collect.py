import random

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.models import (
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


def update_collect_missions(user, plant):
    user_missions = UserMission.objects.filter(
        user=user,
        missionState=MissionState.IN_PROGRESS,
        mission__action=MissionAction.COLLECT,
    ).select_related("mission", "mission__plant")

    for user_mission in user_missions:
        mission = user_mission.mission

        if mission.plant is None or mission.plant == plant:
            user_mission.current += 1

            if mission.goal <= user_mission.current:
                user_mission.missionState = MissionState.COMPLETED

            user_mission.save()


@api_view(["POST"])
@permission_classes([AllowAny])
def collect_plant(request, username, garden_name, pot_number):

    scientificName = request.data.get("plant")

    if not all([username, garden_name, pot_number, scientificName]):
        return Response({"error": "Missing required fields"}, status=400)

    try:
        user = User.objects.get(username=username)
        garden = Garden.objects.get(user=user, name=garden_name)
        pot = Pot.objects.get(garden=garden, number=pot_number)
        plant = Plant.objects.get(scientificName=scientificName)
        plantGarden = PlantInGarden.objects.get(pot=pot, plant=plant)

    except (
        User.DoesNotExist,
        Garden.DoesNotExist,
        Pot.DoesNotExist,
        Plant.DoesNotExist,
        PlantInGarden.DoesNotExist,
    ) as e:
        return Response({"error": f"Resource not found: {str(e)}"}, status=404)

    if plantGarden.growthPhase != GrowthState.MATURE:
        return Response({"error": "Growth phase must be mature"}, status=404)

    plantGarden.delete()

    pot.occupied = False
    pot.save()

    inventory = Inventory.objects.get(user=user)
    inventory.coins += 2
    p = random.randint(1, 100)
    if p < 30:
        inventory.addSeed(scientificName, 1)
    inventory.save()

    user.increment_plants()
    update_collect_missions(user, plant)

    return Response(
        {"message": "Plant collected successfully", "new_balance": inventory.coins},
        status=200,
    )
