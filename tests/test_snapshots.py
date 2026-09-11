"""Tests for the snapshot helpers in ``core.utils.snapshots``.

REQ-AR-002 — the snapshot helpers are the single source of truth for
the data emitted in ``AuditLog.before`` / ``AuditLog.after``. Drift
between call sites was the audit-flagged root cause for the high-severity
resource-snapshot and grant-snapshot duplication.
"""
import pytest

from core.utils.snapshots import resource_snapshot, grant_snapshot, user_role


@pytest.mark.django_db
class TestResourceSnapshot:
    def test_keys_in_canonical_order(self):
        """REQ-AR-002 Scenario 2.1 — fixed key order so JSONField tests
        can assert equality between before/after."""
        from core.models import Resource
        r = Resource.objects.create(name="r1", resource_type="server")
        snap = resource_snapshot(r)
        assert list(snap.keys()) == [
            "name", "resource_type", "environment",
            "url", "is_active", "owner",
        ]

    def test_handles_owner_none(self):
        """REQ-AR-002 Scenario 2.3 — resource with no owner serialises
        ``owner`` as JSON null, never raises AttributeError."""
        from core.models import Resource
        r = Resource.objects.create(name="orphan", resource_type="server", owner=None)
        snap = resource_snapshot(r)
        assert snap["owner"] is None

    def test_owner_serialised_as_username(self):
        """REQ-AR-002 Scenario 2.2 — owner included as username (drift fix)."""
        from core.models import Resource
        from django.contrib.auth.models import User
        owner = User.objects.create_user(username="owner1", password="x")
        r = Resource.objects.create(name="r", resource_type="server", owner=owner)
        snap = resource_snapshot(r)
        assert snap["owner"] == "owner1"


@pytest.mark.django_db
class TestGrantSnapshot:
    def test_keys_in_canonical_order(self):
        from core.models import AccessGrant, Resource
        from django.contrib.auth.models import User
        from django.utils import timezone
        user = User.objects.create_user(username="guser", password="x")
        resource = Resource.objects.create(name="gres", resource_type="server")
        grant = AccessGrant.objects.create(
            user=user,
            resource=resource,
            access_level=AccessGrant.AccessLevel.READ,
            start_at=timezone.now(),
            end_at=timezone.now(),
        )
        snap = grant_snapshot(grant)
        assert list(snap.keys()) == [
            "user", "resource", "access_level", "status",
            "start_at", "end_at", "notes",
        ]

    def test_end_at_serialised_iso_format(self):
        from core.models import AccessGrant, Resource
        from django.contrib.auth.models import User
        from django.utils import timezone
        user = User.objects.create_user(username="guser2", password="x")
        resource = Resource.objects.create(name="gres2", resource_type="server")
        ts = timezone.now()
        grant = AccessGrant.objects.create(
            user=user,
            resource=resource,
            access_level=AccessGrant.AccessLevel.READ,
            start_at=ts,
            end_at=ts,
        )
        snap = grant_snapshot(grant)
        assert snap["end_at"] == ts.isoformat()

    def test_byte_equality_no_drift(self):
        """REQ-AR-002 Scenario 2.4 — same grant snapshot twice must be byte-equal."""
        from core.models import AccessGrant, Resource
        from django.contrib.auth.models import User
        from django.utils import timezone
        user = User.objects.create_user(username="guser3", password="x")
        resource = Resource.objects.create(name="gres3", resource_type="server")
        grant = AccessGrant.objects.create(
            user=user,
            resource=resource,
            access_level=AccessGrant.AccessLevel.READ,
            start_at=timezone.now(),
            end_at=timezone.now(),
        )
        before = grant_snapshot(grant)
        # No intervening mutation
        after = grant_snapshot(grant)
        assert before == after


@pytest.mark.django_db
class TestUserRole:
    def test_returns_group_name(self):
        from django.contrib.auth.models import User, Group
        user = User.objects.create_user(username="role1", password="x")
        user.groups.add(Group.objects.create(name="admin"))
        assert user_role(user) == "admin"

    def test_returns_none_for_group_less_user(self):
        """REQ-AR-002 Scenario 2.5 — user_role returns None (not AttributeError)."""
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="role2", password="x")
        assert user.groups.count() == 0
        assert user_role(user) is None