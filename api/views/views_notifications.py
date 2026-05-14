from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import Device


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_fcm_token(request):
    user = request.user
    token = request.data.get("token")

    if not token:
        return Response({"error": "No token"}, status=400)

    Device.objects.get_or_create(user=user, token=token)

    return Response({"status": "ok"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_fcm_token(request):
    user = request.user
    token = request.data.get("token")

    if not token:
        return Response({"error": "No token"}, status=400)

    Device.objects.filter(user=user, token=token).delete()

    return Response({"status": "deleted"})
