# Importem Q per fer consultes "OR"
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.models import FriendRequest, Garden, User
from api.views.views_translate import translate_text
from api.services.notifications import notify


@api_view(["GET"])
@permission_classes([AllowAny])
def search_users(request):
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
def get_users_friends(request):
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
def delete_friend(request, username):
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
        return Response(
            {"error": translate_text("You are not friends with this user.", lang)},
            status=404,
        )

    friend_request.delete()

    return Response(
        {"success": translate_text(f"Friend {username} deleted successfully.", lang)},
        status=200,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def like_friend(request, username):
    lang = request.user.language
    try:
        friend = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"error": translate_text("User not found.", lang)}, status=404)

    friend_ship = get_friendship(request.user, friend)

    if not friend_ship:
        return Response({"error": translate_text("You are not friends with this user.", lang)}, status=403)

    try:
        garden = Garden.objects.get(user=friend)
    except Garden.DoesNotExist:
        return Response({"error": translate_text("This user does not have a garden yet.", lang)}, status=404)

    like_state = handle_like_action(request, friend_ship, garden)

    friend_ship.save()
    garden.save()

    return Response({"state": like_state, "likes": garden.likes}, status=200)


def get_friendship(user, friend):
    return FriendRequest.objects.filter(
        (Q(requester=user, requested=friend) | Q(requester=friend, requested=user)),
        accepted=True,
    ).first()


def handle_like_action(request, friend_ship, garden):
    if friend_ship.requester == request.user:
        return handle_requested_like(request, friend_ship, garden)

    return handle_requester_like(request, friend_ship, garden)


def handle_requested_like(request, friend_ship, garden):
    if request.method == "POST":
        friend_ship.likeToRequested = toggle_like(
            current_state=friend_ship.likeToRequested,
            garden=garden,
            notified_user=friend_ship.requested,
            liker=request.user,
        )

    return friend_ship.likeToRequested


def handle_requester_like(request, friend_ship, garden):
    if request.method == "POST":
        friend_ship.likeToRequester = toggle_like(
            current_state=friend_ship.likeToRequester,
            garden=garden,
            notified_user=friend_ship.requester,
            liker=request.user,
        )

    return friend_ship.likeToRequester


def toggle_like(current_state, garden, notified_user, liker):
    if current_state:
        garden.likes -= 1
        return False

    garden.likes += 1
    notify(
        notified_user,
        "Like",
        f"This user {liker.username} liked you.",
    )
    return True

