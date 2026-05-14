from datetime import timedelta

from django.utils import timezone
from firebase_admin import messaging

from api.models import Device
from api.services.translate import translate_text

USER_NOTIFICATION_COOLDOWN = timedelta(seconds=0)


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

    response = messaging.send_each_for_multicast(message)

    # eliminar tokens invàlids
    for idx, resp in enumerate(response.responses):
        if not resp.success:
            Device.objects.filter(token=tokens[idx]).delete()


def translate_notification(user, title, body):
    translated = translate_text(
        [title, body],
        user.language,
    )
    return translated[0], translated[1]


# per a que no hi hagi masa spam
def can_send_notification(user):
    if not hasattr(user, "lastNotificationAt"):
        return True

    if not user.lastNotificationAt:
        return True

    return (timezone.now() - user.lastNotificationAt) >= USER_NOTIFICATION_COOLDOWN


def notify(user, title, body):
    translated_title, translated_body = translate_notification(user, title, body)
    send_push_notification(user, translated_title, translated_body)
    user.lastNotificationAt = timezone.now()
    user.save(update_fields=["lastNotificationAt"])

    print(f"[NOTIFICATION] " f"{user.username} | " f"{translated_title}")
