from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from ..models import (
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
def getUserMissions(request):
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
def createMission(request):
    # Check the mandatory fields
    name = request.data.get("name")
    description = request.data.get("description")
    action = request.data.get("action")
    goal = request.data.get("goal")
    plant = request.data.get("plant")
    product = request.data.get("product")
    plantReward = request.data.get("plantReward")
    rewardCoins = request.data.get("rewardCoins")
    productReward = request.data.get("productReward")

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
    if plantReward and not Plant.objects.filter(scientificName=plantReward).exists():
        return Response(
            {"error": f"Plant with scientific name '{plantReward}' does not exist"},
            status=400,
        )
    if product and not Product.objects.filter(name=product).exists():
        return Response({"error": f"Product '{product}' does not exist"})
    if productReward and not Product.objects.filter(name=productReward).exists():
        return Response({"error": f"Product '{productReward}' does not exist"})
    if action not in MissionAction.values:
        return Response(
            {"error": "action must be: PLANT, COLLECT, WATER, FLOWER or DIE"},
            status=400,
        )
    plantIns = Plant.objects.get(scientificName=plant) if plant else None
    plantRewardIns = (
        Plant.objects.get(scientificName=plantReward) if plantReward else None
    )
    productIns = Product.objects.get(name=product) if product else None
    productRewardIns = (
        Product.objects.get(name=productReward) if productReward else None
    )
    Mission.objects.create(
        name=name,
        description=description,
        action=action,
        goal=goal,
        plant=plantIns,
        product=productIns,
        plantReward=plantRewardIns,
        rewardCoins=int(rewardCoins),
        productReward=productRewardIns,
    )
    return Response(
        "Mission created successfully",
    )


# Get missions
@api_view(["GET"])
@permission_classes([AllowAny])
def getMissions(request):
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
@permission_classes([AllowAny])
def assignMission(request):
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
