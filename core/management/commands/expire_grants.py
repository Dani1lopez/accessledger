from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import AccessGrant, AuditLog
from core.utils.log_action import log_action


class Command(BaseCommand):
    help = "Expiración de los permisos"

    def handle(self, *args, **options):
        now = timezone.now()
        # Snapshot the ids BEFORE the bulk update so we can iterate and
        # write audit rows after the status flip.
        affected_pks = list(
            AccessGrant.objects.filter(
                status="active", end_at__lte=now
            ).values_list("pk", flat=True)
        )

        if not affected_pks:
            self.stdout.write(self.style.SUCCESS("0 grants marcados como expirados"))
            return

        updated = AccessGrant.objects.filter(pk__in=affected_pks).update(status="expired")

        # Emit one audit row per expired grant.
        # log_action accepts user=None; AuditLog.user allows NULL.
        for grant in AccessGrant.objects.filter(pk__in=affected_pks):
            log_action(
                user=None,
                action=AuditLog.Action.GRANT_EXPIRED,
                obj=grant,
                before={"status": "active"},
                after={"status": "expired"},
            )

        self.stdout.write(self.style.SUCCESS(
            f"{updated} grants marcados como expirados ({updated} audit rows)"
        ))