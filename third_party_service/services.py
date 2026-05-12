from third_party_service.models import ApiKey


def generate_external_api_token(
    name, created_by=None, expires_at=None, rate_limit="120/min"
):
    return ApiKey.issue_token(
        name=name, created_by=created_by, expires_at=expires_at, rate_limit=rate_limit
    )
