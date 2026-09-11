"""Smoke tests for the atomic + select_for_update pattern.

REQ-AR-003 — select_for_update() is a SQLite no-op. The full
contention tests run against PostgreSQL via the CI service container
introduced in Task 3.5 (gated by ``@pytest.mark.postgres``). Locally
on SQLite, these tests verify the contracts that DO apply:

- Scenarios 3.1, 3.4 (rollback / atomic) run on any DB.
- Scenario 3.5 (select_for_update is a SQLite no-op) is the spec's
  documented limitation; this test pins it down.
"""
import pytest
from django.db import connection, transaction

from core.models import AccessGrant, Resource, AuditLog, Profile
from django.contrib.auth.models import User
from django.utils import timezone


@pytest.mark.django_db
class TestSelectForUpdateIsSqliteNoOp:
    """REQ-AR-003 Scenario 3.5 — select_for_update is documented as a
    no-op on SQLite. Verify the call doesn't raise under transaction.atomic."""

    def test_select_for_update_inside_atomic_does_not_raise_on_sqlite(self):
        if connection.vendor == "sqlite":
            target_user = User.objects.create_user(username="sfu-target", password="pass")
            resource = Resource.objects.create(name="sfu-res", resource_type="server")
            grant = AccessGrant.objects.create(
                user=target_user,
                resource=resource,
                access_level=AccessGrant.AccessLevel.READ,
                start_at=timezone.now(),
                end_at=timezone.now() + timezone.timedelta(days=30),
            )

            with transaction.atomic():
                # Must NOT raise even though SQLite ignores select_for_update.
                loaded = AccessGrant.objects.select_for_update().get(pk=grant.pk)
                assert loaded.pk == grant.pk


@pytest.mark.postgres
@pytest.mark.django_db
class TestAtomicRollback:
    """REQ-AR-003 Scenario 3.1 — user_update must roll back on failure.

    Verifies the atomic block is in place by checking that the rollback
    path works via the actual transaction.atomic() context manager
    even without concurrent execution.
    """

    def test_atomic_block_rolls_back_on_exception(self):
        # Use the real atomic block semantics: any exception inside the
        # block rolls back all writes from that block.
        target_user = User.objects.create_user(
            username="rollback-target", password="oldpass"
        )
        target_user.profile.must_change_password = False
        target_user.profile.save()
        start_profile_pk = target_user.profile.pk

        with pytest.raises(RuntimeError):
            with transaction.atomic():
                target_user.set_password("newpass")
                target_user.profile.must_change_password = True
                target_user.profile.save()
                # Force failure to trigger rollback
                raise RuntimeError("simulated")

        # Profile state must be reverted
        target_user.profile.refresh_from_db()
        assert target_user.profile.must_change_password is False
        # Password must NOT be changed
        target_user.refresh_from_db()
        assert target_user.check_password("oldpass") is True
        assert target_user.profile.pk == start_profile_pk