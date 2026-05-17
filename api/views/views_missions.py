from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import (
    AlbumEntry,
    Inventory,
    Mission,
    MissionAction,
    MissionState,
    Plant,
    Product,
    User,
    UserMission,
)


# Get missions
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_missions(request):
    missions = UserMission.objects.filter(user=request.user)
    return Response(
        {
            "missions": [
                {
                    "Name": mission.mission.name,
                    "Description": mission.mission.description,
                    "Goal": mission.mission.goal,
                    "Action": mission.mission.action,
                    "Plant needed scientific name": (
                        mission.mission.plant.scientificName
                        if mission.mission.plant
                        else None
                    ),
                    "Product needed": (
                        mission.mission.product.name
                        if mission.mission.product
                        else None
                    ),
                    "Plant reward common name": (
                        mission.mission.plantReward.commonName
                        if mission.mission.plantReward
                        else None
                    ),
                    "Plant reward scientific name": (
                        mission.mission.plantReward.scientificName
                        if mission.mission.plantReward
                        else None
                    ),
                    "Reward coins": mission.mission.rewardCoins,
                    "Product reward": (
                        mission.mission.productReward.name
                        if mission.mission.productReward
                        else None
                    ),
                    "Mission state": mission.missionState,
                    "Current number": mission.current,
                    "acquired at": mission.acquiredAt,
                }
                for mission in missions
            ]
        }
    )


# Create mission
@api_view(["POST"])
@permission_classes([AllowAny])
def create_mission(request):
    # Check the mandatory fields
    name = request.data.get("name")
    description = request.data.get("description")
    action = request.data.get("action")
    goal = request.data.get("goal")
    plant = request.data.get("plant")
    product = request.data.get("product")
    plant_reward = request.data.get("plant_reward")
    rewardCoins = request.data.get("rewardCoins")
    product_reward = request.data.get("product_reward")

    if not all([name, description, action]):
        return Response(
            {"error": "name, description and action are required fields"},
            status=400,
        )
    if plant and not Plant.objects.filter(scientificName=plant).exists():
        return Response(
            {"error": f"Plant with scientific name '{plant}' does not exist"},
            status=400,
        )
    if plant_reward and not Plant.objects.filter(scientificName=plant_reward).exists():
        return Response(
            {"error": f"Plant with scientific name '{plant_reward}' does not exist"},
            status=400,
        )
    if product and not Product.objects.filter(name=product).exists():
        return Response({"error": f"Product '{product}' does not exist"})
    if product_reward and not Product.objects.filter(name=product_reward).exists():
        return Response({"error": f"Product '{product_reward}' does not exist"})
    if action not in MissionAction.values:
        return Response(
            {"error": "action must be: PLANT, COLLECT, WATER, FLOWER or DIE"},
            status=400,
        )
    plantIns = Plant.objects.get(scientificName=plant) if plant else None
    plant_reward_ins = (
        Plant.objects.get(scientificName=plant_reward) if plant_reward else None
    )
    product_ins = Product.objects.get(name=product) if product else None
    product_reward_ins = (
        Product.objects.get(name=product_reward) if product_reward else None
    )
    Mission.objects.create(
        name=name,
        description=description,
        action=action,
        goal=goal,
        plant=plantIns,
        product=product_ins,
        plantReward=plant_reward_ins,
        rewardCoins=int(rewardCoins),
        productReward=product_reward_ins,
    )
    return Response(
        "Mission created successfully",
    )


# Get missions
@api_view(["GET"])
@permission_classes([AllowAny])
def get_missions(request):
    missions = Mission.objects.all()
    return Response(
        {
            "missions": [
                {
                    "name": mission.name,
                    "description": mission.description,
                    "action": mission.action,
                    "goal": mission.goal,
                    "plant": mission.plant,
                    "product": mission.product,
                    "plantReward": mission.plantReward,
                    "rewardCoins": mission.rewardCoins,
                    "productReward": mission.productReward,
                }
                for mission in missions
            ]
        }
    )


# Assign mission to user
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assign_mission(request):
    try:
        mission = Mission.objects.get(name=request.data["mission"])
    except Mission.DoesNotExist:
        return Response({"error": "Mission does not exist"}, status=400)

    try:
        user = User.objects.get(username=request.data["user"])
    except User.DoesNotExist:
        return Response({"error": "User does not exist"}, status=400)

    UserMission.objects.create(
        user=user,
        mission=mission,
        current=0,
        missionState=MissionState.IN_PROGRESS,
        acquiredAt=timezone.now(),
    )
    return Response(
        f"Mission assigned to user '{user.username}'",
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def claim_reward(request):
    mission = Mission.objects.get(name=request.data["mission"])
    user_mission = UserMission.objects.get(user=request.user, mission=mission)
    inventory = Inventory.objects.get(user=request.user)
    if not user_mission:  # No existeix la missió
        return Response({"error": "Mission does not exist"}, status=400)
    if user_mission.missionState == MissionState.CLAIMED:  # La missió ja esta reclamada
        return Response({"error": "Mission already claimed"})
    elif (
        user_mission.missionState == MissionState.IN_PROGRESS
    ):  # La missió encara es troba en progrés
        return Response({"error": "Mission in progress"})

    if mission.rewardCoins:
        # Reclamar monedes
        inventory.coins += int(mission.rewardCoins)
    if mission.productReward:
        inventory.addProduct(mission.productReward.name, 1)
    if mission.plantReward:
        plant = Plant.objects.get(scientificName=mission.plantReward.scientificName)
        album_entry = AlbumEntry.objects.filter(user=request.user, plant=plant)
        if not album_entry:
            AlbumEntry.objects.create(user=request.user, plant=plant)
        inventory.addSeed(mission.plantReward.scientificName, 1)
    inventory.save()
    user_mission.missionState = MissionState.CLAIMED
    user_mission.save()
    return Response(
        {
            "message": "Mission claimed successfully",
            "coins": f"{mission.rewardCoins} coins claimed successfully",
            "product": (
                f"{mission.productReward.name} claimed successfully"
                if mission.productReward
                else None
            ),
            "plant": (
                f"{mission.plantReward.scientificName} claimed successfully"
                if mission.plantReward
                else None
            ),
        }
    )
