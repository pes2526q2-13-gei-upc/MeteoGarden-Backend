import hashlib
import re
import secrets

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from config import settings

RATE_LIMIT_PATTERN = re.compile(r"^\d+\/(min|day|sec|hour)$")


class ApiKey(models.Model):
    name = models.CharField(max_length=120, unique=True)
    key_prefix = models.CharField(max_length=16, db_index=True, editable=False)
    key_hash = models.CharField(max_length=64, unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="external_api_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    rate_limit = models.CharField(max_length=32, default="120/min")
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def _generate_raw_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def issue_token(
        cls,
        *,
        name: str,
        created_by=None,
        expires_at=None,
        rate_limit: str = "120/min",
    ) -> tuple["ApiKey", str]:
        raw_token = cls._generate_raw_token()
        token = cls(
            name=name,
            created_by=created_by,
            expires_at=expires_at,
            rate_limit=rate_limit,
            key_prefix=raw_token[:16],
            key_hash=cls.hash_token(raw_token),
        )
        token.full_clean()
        token.save()
        return token, raw_token

    @property
    def is_active(self) -> bool:
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at <= timezone.now():
            return False
        return True

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])

    def clean(self):
        if not RATE_LIMIT_PATTERN.match(self.rate_limit):
            raise ValidationError(
                {
                    "rate_limit": (
                        "rate_limit must follow '<requests>/<period>' format, "
                        "for example '60/min' or '365/day'."
                    )
                }
            )
