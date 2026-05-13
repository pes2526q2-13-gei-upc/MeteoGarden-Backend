from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import FriendRequest, User
from api.views.views_translate import translate_text


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sendFriendRequest(request):
    lang = request.user.language
    requested_name = request.data.get("requested")
    try:
        requested = User.objects.get(username=requested_name)
    except User.DoesNotExist:
        return Response(
            {"error": translate_text(f"User '{requested_name}' doesn't exist", lang)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if requested == request.user:
        return Response(
            {"error": translate_text("A user can't send a friend request to himself.", lang)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    existing = FriendRequest.objects.filter(requester=request.user, requested=requested)
    if existing:
        return Response(
            {
                "error": translate_text(f"User '{request.user.username}' already sent a request to '{requested_name}'", lang)
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    existing_aux = FriendRequest.objects.filter(
        requester=requested, requested=request.user
    )
    if existing_aux:
        return Response(
            {
                "error":
                translate_text(
                    f"User '{requested_name}' already sent a request to '{request.user.username}'",
                    lang,
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    FriendRequest.objects.create(
        requester=request.user, requested=requested, accepted=None
    )
    return Response({translate_text("Request sent successfully", lang)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def answerRequest(request):
    lang = request.user.language
    action = request.data.get("action")
    if action is None:
        return Response(
            {"error": translate_text("Field action is mandatory.", lang)}, status=status.HTTP_400_BAD_REQUEST
        )
    user = request.user
    requester_name = request.data.get("requester")
    try:
        requester = User.objects.get(username=requester_name)
    except User.DoesNotExist:
        return Response(
            {"error": translate_text(f"User '{requester_name}' doesn't exist", lang)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        friendRequest = FriendRequest.objects.get(requested=user, requester=requester)
    except FriendRequest.DoesNotExist:
        return Response(
            {"error": translate_text("Friend request doesn't exist", lang)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if friendRequest.accepted is not None:
        return Response(
            {"error": translate_text("Friend request is already answered", lang)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if action == "accept":
        friendRequest.accepted = True
        friendRequest.save()
        return Response({translate_text("Request accepted successfully", lang)})
    if action == "reject":
        friendRequest.accepted = False
        friendRequest.save()
        return Response({translate_text("Request rejected successfully", lang)})
    return Response(
        {"error": translate_text("Action field is not correct", lang)}, status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancelRequest(request):
    lang = request.user.language
    requested_name = request.data.get("requested")
    requested = User.objects.get(username=requested_name)
    try:
        friendRequest = FriendRequest.objects.get(
            requester=request.user, requested=requested
        )
    except FriendRequest.DoesNotExist:
        return Response(
            {"error": translate_text("Friend request doesn't exist", lang)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not friendRequest:
        return Response(
            {"error": translate_text("Friend request doesn't exist", lang)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if friendRequest.accepted is not None:
        return Response(
            {"error": translate_text("Friend request is already answered'", lang)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # else
    friendRequest.delete()
    return Response(
        {translate_text("Request canceled successfully", lang)}
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getRequests(request):
    lang = request.user.language
    action = request.data.get("action")
    if action == "sent":
        requests = FriendRequest.objects.filter(requester=request.user, accepted=None)
        return Response({"requests_sent to": [r.requested.username for r in requests]})
    elif action == "received":
        requests = FriendRequest.objects.filter(requested=request.user, accepted=None)
        return Response(
            {"requests_received from": [r.requester.username for r in requests]}
        )
    else:
        return Response(
            {"error": translate_text("Field action must be 'sent' or 'received'.", lang)},
            status=status.HTTP_400_BAD_REQUEST,
        )
