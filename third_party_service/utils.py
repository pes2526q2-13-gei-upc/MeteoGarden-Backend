import secrets

from third_party_service.models import ApiKey


def generate_api_key(user, name=""):
    key = secrets.token_hex(32)
    api_key = ApiKey.objects.create(key=key, user=user, name=name)
    return api_key
