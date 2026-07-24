"""Idempotent env-driven superuser + admin-group bootstrap.

Reads DJANGO_SUPERUSER_USERNAME / _PASSWORD / _EMAIL via os.environ (values
are data, never shell/Python source). On a fresh deploy, creates the
superuser and the admin group with the standard permission set. Re-runs
are no-ops for existing users (no password/email overwrite).

Exit semantics:
- env vars missing → exit 0, WARNING log (intentional skip).
- env vars present, any error → exit 1 via CommandError (fail-closed).

Decision (a'): admin-group permissions are seeded from the shared
``ADMIN_GROUP_PERMISSIONS`` constant so this command and
``bootstrap_roles`` stay in sync.
"""
import os

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import EmailValidator, ValidationError
from django.db import OperationalError

from core.models import Resource
from core.permissions.constants import ADMIN_GROUP_PERMISSIONS


class Command(BaseCommand):
    help = "Idempotent env-driven superuser + admin-group bootstrap."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "If set, overwrite the password and email of an existing user. "
                "Default behavior is idempotent: existing credentials are preserved."
            ),
        )

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        reset = options.get("reset", False)

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                "[ensure_superuser] SKIP: DJANGO_SUPERUSER_USERNAME/PASSWORD not set"
            ))
            return

        if email:
            try:
                EmailValidator()(email)
            except ValidationError as exc:
                raise CommandError(f"[ensure_superuser] invalid email: {exc}")

        admin, _ = Group.objects.get_or_create(name="admin")
        # Seed admin permissions from the shared constant (decision a'):
        # compose with bootstrap_roles via shared source of truth.
        for codename in ADMIN_GROUP_PERMISSIONS:
            try:
                ct = ContentType.objects.get_for_model(Resource)
                perm = Permission.objects.get(content_type=ct, codename=codename)
            except Permission.DoesNotExist:
                # Custom permission (can_grant_access / can_revoke_access) has
                # no ContentType binding — look up by codename only.
                try:
                    perm = Permission.objects.get(codename=codename)
                except Permission.DoesNotExist:
                    # Codename not registered yet — skip without failing.
                    continue
            admin.permissions.add(perm)

        try:
            user, created = User.objects.get_or_create(username=username)
        except OperationalError as exc:
            raise CommandError(f"[ensure_superuser] DB error: {exc}")

        if created or reset:
            user.set_password(password)
            user.email = email
            user.is_staff = True
            user.is_superuser = True
            user.save()

        user.groups.add(admin)  # idempotent

        action = "created" if created else "already exists"
        self.stdout.write(self.style.SUCCESS(
            f"[ensure_superuser] {action} superuser: {username}"
        ))
