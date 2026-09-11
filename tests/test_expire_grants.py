"""Tests for the expire_grants management command.

REQ-AR-004 — expire_grants MUST emit one AuditLog row per expired
grant with user=None, action=GRANT_EXPIRED, before={status: active},
after={status: expired}.
"""
import io
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone

from core.models import AccessGrant, AuditLog, Resource


@pytest.mark.django_db
class TestExpireGrants:
    def test_emits_audit_row_per_expired_grant(self):
        """REQ-AR-004 Scenario 4.1 — 3 expired grants → 3 audit rows."""
        target = User.objects.create_user(username="exp-target", password="pass")
        resource = Resource.objects.create(name="exp-res", resource_type="server")
        past = timezone.now() - timedelta(days=30)
        for i in range(3):
            AccessGrant.objects.create(
                user=target,
                resource=resource,
                access_level=AccessGrant.AccessLevel.READ,
                start_at=past - timedelta(days=30),
                end_at=past,
            )

        call_command("expire_grants", stdout=io.StringIO())

        # All three grants are now expired
        assert AccessGrant.objects.filter(status="expired").count() == 3
        # Three audit rows emitted
        rows = AuditLog.objects.filter(action=AuditLog.Action.GRANT_EXPIRED)
        assert rows.count() == 3
        for row in rows:
            assert row.user is None
            assert row.before == {"status": "active"}
            assert row.after == {"status": "expired"}

    def test_zero_affected_zero_audit_rows(self):
        """REQ-AR-004 Scenario 4.2 — nothing to expire → nothing written."""
        # No grants in DB
        call_command("expire_grants", stdout=io.StringIO())
        assert AuditLog.objects.filter(action=AuditLog.Action.GRANT_EXPIRED).count() == 0

    def test_audit_log_user_null_is_permitted(self):
        """REQ-AR-004 Scenario 4.3 — AuditLog.user allows NULL."""
        from core.utils.log_action import log_action
        target = User.objects.create_user(username="null-target", password="pass")
        resource = Resource.objects.create(name="null-res", resource_type="server")
        grant = AccessGrant.objects.create(
            user=target,
            resource=resource,
            access_level=AccessGrant.AccessLevel.READ,
            start_at=timezone.now() - timedelta(days=30),
            end_at=timezone.now() - timedelta(days=1),
        )
        log_action(
            user=None,
            action=AuditLog.Action.GRANT_EXPIRED,
            obj=grant,
            before={"status": "active"},
            after={"status": "expired"},
        )
        row = AuditLog.objects.get(object_id=grant.pk)
        assert row.user is None

    def test_does_not_emit_for_active_grants_in_future(self):
        """A grant with end_at in the future is NOT expired; no audit row."""
        target = User.objects.create_user(username="future-target", password="pass")
        resource = Resource.objects.create(name="future-res", resource_type="server")
        AccessGrant.objects.create(
            user=target,
            resource=resource,
            access_level=AccessGrant.AccessLevel.READ,
            start_at=timezone.now(),
            end_at=timezone.now() + timedelta(days=30),
        )
        call_command("expire_grants", stdout=io.StringIO())
        assert AuditLog.objects.filter(action=AuditLog.Action.GRANT_EXPIRED).count() == 0