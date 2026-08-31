"""Idempotent env-driven superuser + admin-group bootstrap.

Reads DJANGO_SUPERUSER_USERNAME / _PASSWORD / _EMAIL via os.environ (values
are data, never shell/Python source). On a fresh deploy, creates the
superuser and the admin group with the standard permission set. Re-runs
are no-ops for existing users (no password/email overwrite).

Safety rule for existing users: an account that already exists but is
not a superuser is treated as a username collision. The command fails
closed with a CommandError rather than silently promoting a non-superuser
account to the admin group. Use ``--reset`` to explicitly promote/update
the configured account.

Exit semantics:
- env vars missing → exit 0, WARNING log (intentional skip).
- env vars present, any error → exit 1 via CommandError (fail-closed).

Decision (a'): admin-group permissions are seeded from the shared
``ADMIN_GROUP_PERMISSIONS`` constant so this command and
``bootstrap_roles`` stay in sync.
"""
import os

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import EmailValidator, ValidationError
from django.db import OperationalError, transaction

from core.permissions._bootstrap import seed_admin_permissions


class Command(BaseCommand):
    help = (
        "Idempotent env-driven superuser + admin-group bootstrap. "
        "Fails closed if the configured username already belongs to a non-superuser account; "
        "use --reset to promote/update an existing account."
    )

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

        try:
            with transaction.atomic():
                # Group + permissions seeding now lives INSIDE the atomic
                # block so a mid-transaction failure leaves no admin group
                # with partial permissions (REQ-AR-003 Scenario 3.4).
                admin, _ = Group.objects.get_or_create(name="admin")
                seed_admin_permissions(admin)

                user, created = User.objects.get_or_create(username=username)

                if created or reset:
                    user.set_password(password)
                    user.email = email
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()

                if not created and not reset and not user.is_superuser:
                    raise CommandError(
                        f"[ensure_superuser] existing user '{username}' is not a superuser; "
                        f"refusing to grant admin group. Use --reset to promote/update."
                    )

                user.groups.add(admin)  # idempotent
        except OperationalError as exc:
            raise CommandError(f"[ensure_superuser] DB error: {exc}")

        action = "created" if created else "already exists"
        self.stdout.write(self.style.SUCCESS(
            f"[ensure_superuser] {action} superuser: {username}"
        ))
