# Importem Q per fer consultes "OR"
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.models import FriendRequest, Garden, User


@api_view(["GET"])
@permission_classes([AllowAny])
def searchUsers(request):
    query = request.query_params.get("q", "")

    if query:
        users = User.objects.filter(username__icontains=query)[:10]  # Límit de 10
    else:
        users = User.objects.none()

    results = []
    for u in users:
        results.append({"username": u.username})

    return Response(results)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getUsersFriends(request):
    user = request.user

    friend_requests = FriendRequest.objects.filter(
        (Q(requester=user) | Q(requested=user)), accepted=True
    )

    friends_list = []

    for fr in friend_requests:
        friend_user = fr.requested if fr.requester == user else fr.requester

        friends_list.append(
            {
                "username": friend_user.username,
                "garden": Garden.objects.filter(user=friend_user).first().name,
            }
        )

    return Response({"friends": friends_list})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def deleteFriend(request, username):
    try:
        friend = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=404)

    friend_request = FriendRequest.objects.filter(
        (
            Q(requester=request.user, requested=friend)
            | Q(requester=friend, requested=request.user)
        ),
        accepted=True,
    ).first()

    if not friend_request:
        return Response({"error": "You are not friends with this user."}, status=404)

    friend_request.delete()

    return Response({"success": f"Friend {username} deleted successfully."}, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def likeFriend(request, username):
    try:
        friend = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=404)

    friend_ship = FriendRequest.objects.filter(
        (
            Q(requester=request.user, requested=friend)
            | Q(requester=friend, requested=request.user)
        ),
        accepted=True,
    ).first()

    if not friend_ship:
        return Response(
            {"error": "You are not friends with this user."}, status=403
        )

    try:
        garden = Garden.objects.get(user=friend)
        if friend_ship.requester == request.user:
            if friend_ship.likeToRequested:
                garden.likes -= 1
                friend_ship.likeToRequested = False
            else:
                garden.likes += 1
                friend_ship.likeToRequested = True
        else :
            if friend_ship.likeToRequester:
                garden.likes -= 1
                friend_ship.likeToRequester = False
            else:
                garden.likes += 1
                friend_ship.likeToRequester = True
        friend_ship.save()
        garden.save()
    except Garden.DoesNotExist:
        return Response(
            {"error": "This user does not have a garden yet."}, status=404
        )

    return Response({"success": f"Total likes: {garden.likes}"}, status=200)
