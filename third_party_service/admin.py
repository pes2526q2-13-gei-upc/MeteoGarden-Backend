from django.contrib import admin
from .models import ApiKey

@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = [
        "name", "key_prefix", "created_by", "created_at", "expires_at", "revoked_at", "rate_limit", "is_active"
    ]
    list_filter = [
        "created_by", "revoked_at", "expires_at", "rate_limit"
    ]
    search_fields = ["name", "key_prefix", "created_by__username"]
    readonly_fields = ["key_prefix", "key_hash", "created_at", "last_used_at", "is_active"]
    ordering = ["-created_at"]
    actions = ["revoke_tokens"]

    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = "Active?"

    def revoke_tokens(self, request, queryset):
        count = 0
        for obj in queryset:
            obj.revoke()
            count += 1
        self.message_user(request, f"{count} tokens revocats.")
    revoke_tokens.short_description = "Revocar tokens seleccionats"

    def get_readonly_fields(self, request, obj=None):
        # No deixar editar camps clau!
        ro = list(self.readonly_fields)
        if obj:
            ro += ["name", "created_by", "created_at", "key_prefix", "key_hash"]
        return ro