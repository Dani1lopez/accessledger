"""Tests for ``_is_ajax`` and ``_audit`` view helpers.

REQ-AR-005 — these helpers centralise the duplicated is-ajax check
and the form.is_valid → save → log_action pattern that was audited
across 6 views.
"""
import pytest
from django.test import RequestFactory

from core.utils.log_action import log_action
from core.views import _is_ajax, _audit
from core.models import AuditLog


class TestIsAjax:
    def setup_method(self):
        self.factory = RequestFactory()

    def test_returns_true_for_ajax_header(self):
        """REQ-AR-005 Scenario 5.1 — X-Requested-With: XMLHttpRequest returns True."""
        request = self.factory.get("/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert _is_ajax(request) is True

    def test_returns_false_without_header(self):
        request = self.factory.get("/")
        assert _is_ajax(request) is False


@pytest.mark.django_db
class TestAuditContextManager:
    def setup_method(self):
        self.factory = RequestFactory()
        self.request = self.factory.post("/")
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username="actor", password="x")

    def test_writes_audit_log_on_success(self):
        """REQ-AR-005 Scenario 5.2 — log row written on success."""
        from core.models import Resource
        resource = Resource.objects.create(name="audit-res", resource_type="server")

        with _audit(
            action=AuditLog.Action.RESOURCE_CREATED,
            user=self.user,
            obj=resource,
            before=None,
        ):
            pass  # body is empty in this test

        rows = AuditLog.objects.filter(
            object_id=resource.pk,
            action=AuditLog.Action.RESOURCE_CREATED,
        )
        assert rows.count() == 1
        # after is the resource snapshot (Scenario 5.4)
        row = rows.first()
        assert row.after["name"] == "audit-res"

    def test_uses_matching_snapshot_helper(self):
        """REQ-AR-005 Scenario 5.4 — after equals the matching snapshot helper."""
        from core.models import AccessGrant, Resource
        from django.utils import timezone
        from core.utils.snapshots import grant_snapshot

        resource = Resource.objects.create(name="rf", resource_type="server")
        grant = AccessGrant.objects.create(
            user=self.user,
            resource=resource,
            access_level=AccessGrant.AccessLevel.READ,
            start_at=timezone.now(),
            end_at=timezone.now(),
        )

        with _audit(
            action=AuditLog.Action.GRANT_CREATED,
            user=self.user,
            obj=grant,
            before=None,
        ):
            pass

        row = AuditLog.objects.filter(object_id=grant.pk).first()
        assert row.after == grant_snapshot(grant)

    def test_no_log_on_exception(self):
        """REQ-AR-005 Scenario 5.3 — exception inside the block suppresses the log row."""
        from core.models import Resource
        resource = Resource.objects.create(name="exc-res", resource_type="server")

        with pytest.raises(RuntimeError):
            with _audit(
                action=AuditLog.Action.RESOURCE_CREATED,
                user=self.user,
                obj=resource,
                before=None,
            ):
                raise RuntimeError("simulated")

        # Audit row MUST NOT be persisted — atomic block rolled back.
        assert AuditLog.objects.filter(object_id=resource.pk).count() == 0