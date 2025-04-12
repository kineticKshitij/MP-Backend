from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = "Delete all superusers"

    def handle(self, *args, **kwargs):
        superusers = User.objects.filter(is_superuser=True)
        count = superusers.count()
        superusers.delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} superuser(s).'))
