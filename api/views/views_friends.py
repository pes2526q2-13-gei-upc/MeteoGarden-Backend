# Importem Q per fer consultes "OR"
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.models import FriendRequest, Garden, User
from api.views.views_translate import translate_text


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
        results.append(
            {"username": u.username, "avatar": u.avatar.url if u.avatar else None}
        )

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
                "avatar": friend_user.avatar.url if friend_user.avatar else None,
                "garden": Garden.objects.filter(user=friend_user).first().name,
            }
        )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def deleteFriend(request, username):
    lang = request.user.language
    try:
        friend = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"error": translate_text("User not found.", lang)}, status=404)

    friend_request = FriendRequest.objects.filter(
        (
            Q(requester=request.user, requested=friend)
            | Q(requester=friend, requested=request.user)
        ),
        accepted=True,
    ).first()

    if not friend_request:
        return Response({"error": translate_text("You are not friends with this user.", lang)}, status=404)

    friend_request.delete()

    return Response({"success": translate_text(f"Friend {username} deleted successfully.", lang)}, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def likeFriend(request, username):
    lang = request.user.language
    try:
        friend = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"error": translate_text("User not found.", lang)}, status=404)

    is_friend = FriendRequest.objects.filter(
        (
            Q(requester=request.user, requested=friend)
            | Q(requester=friend, requested=request.user)
        ),
        accepted=True,
    ).exists()

    if not is_friend:
        return Response(
            {"error": translate_text("You are not friends with this user.", lang)}, status=403
        )

    try:
        garden = Garden.objects.get(user=friend)
        garden.likes += 1
        garden.save()
    except Garden.DoesNotExist:
        return Response(
            {"error": translate_text("This user does not have a garden yet.", lang)}, status=404
        )

    return Response({"success": translate_text(f"Total likes: {garden.likes}", lang)}, status=200)
