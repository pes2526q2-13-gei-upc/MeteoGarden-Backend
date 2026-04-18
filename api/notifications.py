from firebase_admin import messaging
from api.models import Device
from django.utils import timezone
from datetime import timedelta

def send_push_notification(user, title, body):
    devices = Device.objects.filter(user=user)
    tokens = [d.token for d in devices if d.token]

    if not tokens:
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        tokens=tokens,
    )

    response = messaging.send_multicast(message)

    # eliminar tokens invàlids
    for idx, resp in enumerate(response.responses):
        if not resp.success:
            Device.objects.filter(token=tokens[idx]).delete()

# per a que no hi hagi masa spam (max cada 2 hores)
def can_send_notification(pig):
    if not pig.lastNotificationAt:
        return True

    return (timezone.now() - pig.lastNotificationAt) > timedelta(hours=2)