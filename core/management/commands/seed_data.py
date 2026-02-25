from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import timedelta
from core.models import Resource, AccessGrant


class Command(BaseCommand):
    help = "Crea datos de prueba para Resources y AccessGrants"

    def handle(self, *args, **options):
        self.stdout.write("seed_data running...")

        viewer1, created = User.objects.get_or_create(username="viewer1")
        if created:
            viewer1.set_password("viewer1234!")
            viewer1.groups.add(Group.objects.get(name="viewer"))
            viewer1.save()
        editor1, created = User.objects.get_or_create(username="editor1")
        if created:
            editor1.set_password("edit1234!")
            editor1.groups.add(Group.objects.get(name="editor"))
            editor1.save()
        admin1, created = User.objects.get_or_create(username="admin1")
        if created:
            admin1.set_password("admin1234!")
            admin1.groups.add(Group.objects.get(name="admin"))
            admin1.save()

        now = timezone.now()

        # ── Resources ──────────────────────────────────────────────
        resources_data = [
            {
                "name": "api-gateway-prod",
                "resource_type": Resource.ResourceType.SERVER,
                "environment": Resource.Environment.PROD,
                "url": "https://api.acme.internal",
                "owner": admin1,
                "is_active": True,
            },
            {
                "name": "frontend-repo",
                "resource_type": Resource.ResourceType.REPO,
                "environment": Resource.Environment.NA,
                "url": "https://github.com/acme/frontend",
                "owner": editor1,
                "is_active": True,
            },
            {
                "name": "db-postgres-prod",
                "resource_type": Resource.ResourceType.DATABASE,
                "environment": Resource.Environment.PROD,
                "url": "postgresql://db.acme.internal:5432/main",
                "owner": admin1,
                "is_active": True,
            },
            {
                "name": "datadog-dashboard",
                "resource_type": Resource.ResourceType.DASHBOARD,
                "environment": Resource.Environment.PROD,
                "url": "https://app.datadoghq.com/dashboard/acme",
                "owner": editor1,
                "is_active": True,
            },
            {
                "name": "vpn-office",
                "resource_type": Resource.ResourceType.VPN,
                "environment": Resource.Environment.NA,
                "url": "",
                "owner": admin1,
                "is_active": True,
            },
            {
                "name": "notion-workspace",
                "resource_type": Resource.ResourceType.SAAS,
                "environment": Resource.Environment.NA,
                "url": "https://notion.so/acme",
                "owner": editor1,
                "is_active": True,
            },
            {
                "name": "staging-server",
                "resource_type": Resource.ResourceType.SERVER,
                "environment": Resource.Environment.STAGING,
                "url": "https://staging.acme.internal",
                "owner": admin1,
                "is_active": True,
            },
            {
                "name": "backend-repo",
                "resource_type": Resource.ResourceType.REPO,
                "environment": Resource.Environment.NA,
                "url": "https://github.com/acme/backend",
                "owner": editor1,
                "is_active": False,  # inactivo a propósito para probar filtros
            },
        ]

        resources = {}
        for data in resources_data:
            obj, created = Resource.objects.get_or_create(name=data["name"], defaults=data)
            resources[obj.name] = obj
            status = "✅ creado" if created else "⏭️  ya existe"
            self.stdout.write(f"  {status}: {obj.name}")

        # ── AccessGrants ───────────────────────────────────────────
        grants_data = [
            # viewer1 — acceso de lectura a varios recursos
            {
                "user": viewer1,
                "resource": resources["datadog-dashboard"],
                "access_level": AccessGrant.AccessLevel.READ,
                "status": AccessGrant.Status.ACTIVE,
                "start_at": now - timedelta(days=30),
                "end_at": now + timedelta(days=60),
                "notes": "Acceso de monitorización para QA.",
            },
            {
                "user": viewer1,
                "resource": resources["frontend-repo"],
                "access_level": AccessGrant.AccessLevel.READ,
                "status": AccessGrant.Status.ACTIVE,
                "start_at": now - timedelta(days=10),
                "end_at": now + timedelta(days=80),
                "notes": "Revisión de código sin permisos de escritura.",
            },
            # editor1 — acceso write a repos y staging
            {
                "user": editor1,
                "resource": resources["frontend-repo"],
                "access_level": AccessGrant.AccessLevel.WRITE,
                "status": AccessGrant.Status.ACTIVE,
                "start_at": now - timedelta(days=60),
                "end_at": now + timedelta(days=120),
                "notes": "",
            },
            {
                "user": editor1,
                "resource": resources["staging-server"],
                "access_level": AccessGrant.AccessLevel.WRITE,
                "status": AccessGrant.Status.ACTIVE,
                "start_at": now - timedelta(days=5),
                "end_at": now + timedelta(days=30),
                "notes": "Despliegues en staging.",
            },
            {
                "user": editor1,
                "resource": resources["backend-repo"],
                "access_level": AccessGrant.AccessLevel.WRITE,
                "status": AccessGrant.Status.REVOKED,
                "start_at": now - timedelta(days=90),
                "end_at": now - timedelta(days=10),
                "notes": "Acceso revocado al archivar el repo.",
            },
            # admin1 — acceso admin a producción
            {
                "user": admin1,
                "resource": resources["api-gateway-prod"],
                "access_level": AccessGrant.AccessLevel.ADMIN,
                "status": AccessGrant.Status.ACTIVE,
                "start_at": now - timedelta(days=180),
                "end_at": now + timedelta(days=180),
                "notes": "Responsable principal del gateway.",
            },
            {
                "user": admin1,
                "resource": resources["db-postgres-prod"],
                "access_level": AccessGrant.AccessLevel.ADMIN,
                "status": AccessGrant.Status.ACTIVE,
                "start_at": now - timedelta(days=180),
                "end_at": now + timedelta(days=180),
                "notes": "DBA de producción.",
            },
            {
                "user": admin1,
                "resource": resources["vpn-office"],
                "access_level": AccessGrant.AccessLevel.ADMIN,
                "status": AccessGrant.Status.ACTIVE,
                "start_at": now - timedelta(days=365),
                "end_at": now + timedelta(days=365),
                "notes": "",
            },
            # grant expirado — para probar el estado expired
            {
                "user": viewer1,
                "resource": resources["staging-server"],
                "access_level": AccessGrant.AccessLevel.READ,
                "status": AccessGrant.Status.EXPIRED,
                "start_at": now - timedelta(days=120),
                "end_at": now - timedelta(days=30),
                "notes": "Acceso temporal para auditoría.",
            },
        ]

        for data in grants_data:
            obj, created = AccessGrant.objects.get_or_create(
                user=data["user"],
                resource=data["resource"],
                defaults=data,
            )
            status = "✅ creado" if created else "⏭️  ya existe"
            self.stdout.write(f"  {status}: {obj}")

        self.stdout.write(self.style.SUCCESS(
            f"\nFin. Resources: {Resource.objects.count()} | "
            f"AccessGrants: {AccessGrant.objects.count()}"
        ))