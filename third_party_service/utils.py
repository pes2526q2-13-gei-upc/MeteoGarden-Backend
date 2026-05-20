from third_party_service.models import ApiKey


def generate_api_key(user, name=""):
    api_key_obj, raw_token = ApiKey.issue_token(name=name, created_by=user)
    return api_key_obj
