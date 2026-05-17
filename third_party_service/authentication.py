from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from third_party_service.models import ApiKey  # Ajusta el camí al teu model


class ApiKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # 1. Obtenim la clau de la capçalera o de la URL
        key = request.headers.get("X-API-KEY")

        if not key:
            return (
                None  # No es proporciona clau, passem al següent sistema d'autenticació
            )

        key = key.strip()
        if len(key) < 16:
            raise AuthenticationFailed("Invalid API key format")

        prefix = key[:16]
        hashed = ApiKey.hash_token(key)

        try:
            token = ApiKey.objects.get(key_prefix=prefix, key_hash=hashed)

            if not token.is_active:
                raise AuthenticationFailed("API key is expired or revoked")

            token.last_used_at = timezone.now()
            token.save(update_fields=["last_used_at"])

            # COMPROVACIÓ MILLORADA:
            if token.created_by:
                user = token.created_by
            else:
                # Si no té usuari humà, usem el mateix objecte token com a "usuari virtual"
                # Però li diem a Django que el consideri com a autenticat de mentida
                user = token
                user.is_authenticated = (
                    True  # <--- Truc màgic per saltar IsAuthenticated
                )

            return user, token

        except ApiKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API key")
