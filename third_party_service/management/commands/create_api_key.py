from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from third_party_service.utils import generate_api_key

class Command(BaseCommand):
    help = "Genera una API Key per a un usuari"

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)

    def handle(self, *args, **options):
        username = options['username']
        User = get_user_model()
        user = User.objects.get(username=username)
        api_key = generate_api_key(user)
        self.stdout.write(f"API Key per {user.username}: {api_key.key}")