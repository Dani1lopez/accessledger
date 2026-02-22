from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import AccessGrant

class Command(BaseCommand):
    help = "Expiración de los permisos"
    
    def handle(self, *args, **options):
        updated =AccessGrant.objects.filter(status="active", end_at__lte=timezone.now()).update(status="expired")
        self.stdout.write(self.style.SUCCESS(f"{updated} grants marcados como expirados"))