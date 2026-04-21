from gunicorn.dirty.stash import exists
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from ..models import Mission, UserMission, Plant, MissionAction, Product


# Get missions
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getUserMissions(request):
    missions = UserMission.objects.filter(user=request.user)
    return Response({"missions": [{
        "Name": mission.mission.name,
        "Description": mission.mission.description,
        "Goal": mission.mission.goal,
        "Action": mission.mission.action,
        "Plant needed scientific name": mission.mission.plant.name,
        "Product needed": mission.mission.product.name,
        "Plant reward common name": mission.mission.plantReward.commonName,
        "Plant reward scientific name": mission.mission.plantReward.scientificName,
        "Reward coins": mission.mission.rewardCoins,
        "Product reward": mission.mission.productReward.name,
        "Mission state": mission.missionState,
        "Current number": mission.current,
        "acquired at": mission.acquiredAt,
    } for mission in missions]})

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
            {
                "error": "name, description and action are required fields"
            },
            status=400,
        )
    if not Plant.objects.filter(name=plant).exists():
        return Response(
            {
                "error": f"Plant with scientific name '{seed}' does not exist"
            },
            status=400,
        )
    if not Plant.objects.filter(name=plantReward).exists():
        return Response(
            {
                "error": f"Plant with scientific name '{seed}' does not exist"
            },
            status=400,
        )
    if not Plant.objects.filter(name=product).exists():
        return Response(
            {
                "error": f"Product '{product}' does not exist"
            }
        )
    if not Plant.objects.filter(name=productReward).exists():
        return Response(
            {
                "error": f"Product '{productReward}' does not exist"
            }
        )
    if not MissionAction.objects.filter(name=action).exists():
        return Response(
            {
                "error": "action must be: PLANT, COLLECT, WATER, FLOWER or DIE"
             },
            status=400,
        )
    plantIns = Plant.objects.get(name=name)
    plantRewardIns = Plant.objects.get(name=plantReward)
    productIns = Product.objects.get(name=product)
    productRewardIns = Product.objects.get(name=productReward)
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
    return Response({"missions": [{
        "name": mission.name,
        "description": mission.description,
        "action": mission.action,
        "goal": mission.goal,
        "plant": mission.plant,
        "product": mission.product,
        "plantReward": mission.plantReward,
        "rewardCoins": mission.rewardCoins,
        "productReward": mission.productReward,
    } for mission in missions]})