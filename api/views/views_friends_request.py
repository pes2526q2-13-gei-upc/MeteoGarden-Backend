from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import FriendRequest, User
from api.notifications import notify

message = "Friend request doesn't exist"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_friend_request(request):
    requested_name = request.data.get("requested")
    try:
        requested = User.objects.get(username=requested_name)
    except User.DoesNotExist:
        return Response(
            {"error": f"User '{requested_name}' doesn't exist"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if requested == request.user:
        return Response(
            {"error": "A user can't send a friend request to himself."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    existing = FriendRequest.objects.filter(requester=request.user, requested=requested)
    if existing:
        return Response(
            {
                "error": f"User '{request.user.username}' already sent a request to '{requested_name}'"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    existing_aux = FriendRequest.objects.filter(
        requester=requested, requested=request.user
    )
    if existing_aux:
        return Response(
            {
                "error:"
                f"User '{requested_name}' already sent a request to '{request.user.username}'"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    FriendRequest.objects.create(
        requester=request.user, requested=requested, accepted=None
    )
    notify(
        requested,
        "👤 New notification!",
        f"'{request.user.username}' has sent you a friend request!",
    )
    return Response({"Request sent successfully"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def answer_request(request):
    action = request.data.get("action")
    if action is None:
        return Response(
            {"error": "Field action is mandatory."}, status=status.HTTP_400_BAD_REQUEST
        )
    user = request.user
    requester_name = request.data.get("requester")
    try:
        requester = User.objects.get(username=requester_name)
    except User.DoesNotExist:
        return Response(
            {"error": f"User '{requester_name}' doesn't exist"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        friend_request = FriendRequest.objects.get(requested=user, requester=requester)
    except FriendRequest.DoesNotExist:
        return Response(
            {"error": message},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if friend_request.accepted is not None:
        return Response(
            {"error": "Friend request is already answered'"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if action == "accept":
        friend_request.accepted = True
        friend_request.save()
        return Response({"Request accepted successfully"})
    if action == "reject":
        friend_request.accepted = False
        friend_request.save()
        return Response({"Request rejected successfully"})
    return Response(
        {"error": "Action field is not correct"}, status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_request(request):
    requested_name = request.data.get("requested")
    requested = User.objects.get(username=requested_name)
    try:
        friendRequest = FriendRequest.objects.get(
            requester=request.user, requested=requested
        )
    except FriendRequest.DoesNotExist:
        return Response(
            {"error": message},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not friendRequest:
        return Response(
            {"error": message},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if friendRequest.accepted is not None:
        return Response(
            {"error": "Friend request is already answered'"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # else
    friendRequest.delete()
    return Response({"Request canceled successfully"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getRequests(request):
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
            {"error": "Field action must be 'sent' or 'received'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
