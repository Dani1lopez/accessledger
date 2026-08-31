"""Tests for the self-deactivation / last-admin guards in user_toggle_active.

REQ-AR-011 — both guards run BEFORE the atomic block opens so a
rejected request does not acquire a row lock.
"""
import pytest
from django.contrib.auth.models import User
from django.test import Client

from core.models import AuditLog


@pytest.mark.django_db
class TestUserToggleActiveGuards:
    def _make_admin(self, username, email):
        """Create a superuser AND add them to the 'admin' group
        (required by admin_required decorator)."""
        from django.contrib.auth.models import Group
        admin_group, _ = Group.objects.get_or_create(name="admin")
        user = User.objects.create_superuser(
            username=username, password="pass", email=email
        )
        user.groups.add(admin_group)
        user.profile.must_change_password = False
        user.profile.save()
        return user

    def _login_admin(self, client, admin_user):
        client.force_login(admin_user)

    def test_self_deactivation_rejected(self):
        """REQ-AR-011 Scenario 11.1 — admin cannot deactivate themselves."""
        admin = self._make_admin("self-admin", "self@x.com")
        client = Client()
        self._login_admin(client, admin)
        response = client.post(f"/users/{admin.pk}/toggle/")
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert "No puedes desactivarte a ti mismo" in body["errors"]["__all__"][0]

        # No mutation, no DB lock taken
        admin.refresh_from_db()
        assert admin.is_active is True
        # No audit row written
        assert AuditLog.objects.filter(
            object_id=admin.pk,
            action__in=[
                AuditLog.Action.USER_ACTIVATED,
                AuditLog.Action.USER_DEACTIVATED,
            ],
        ).count() == 0

    def test_last_admin_deactivation_rejected(self):
        """REQ-AR-011 Scenario 11.2 — only one active superuser; cannot deactivate."""
        admin = self._make_admin("last-admin", "last@x.com")
        # Other superuser exists but is INACTIVE
        User.objects.create_superuser(
            username="inactive-su", password="pass", email="inactive@x.com"
        )
        User.objects.filter(username="inactive-su").update(is_active=False)

        # Actor is admin (group) but NOT superuser, so the only active
        # superuser is 'admin' (last-admin).
        from django.contrib.auth.models import Group
        actor_group, _ = Group.objects.get_or_create(name="admin")
        actor = User.objects.create_user(username="actor", password="pass")
        actor.groups.add(actor_group)
        actor.profile.must_change_password = False
        actor.profile.save()

        client = Client()
        self._login_admin(client, actor)
        response = client.post(f"/users/{admin.pk}/toggle/")
        assert response.status_code == 400
        body = response.json()
        assert "último superusuario activo" in body["errors"]["__all__"][0]

        admin.refresh_from_db()
        assert admin.is_active is True

    def test_normal_admin_deactivation_allowed(self):
        """REQ-AR-011 Scenario 11.3 — admin1 can be deactivated when admin2 exists."""
        admin1 = self._make_admin("normal-admin1", "n1@x.com")
        admin2 = self._make_admin("normal-admin2", "n2@x.com")
        client = Client()
        self._login_admin(client, admin2)
        response = client.post(f"/users/{admin1.pk}/toggle/")
        assert response.status_code == 200
        assert response.json()["success"] is True

        admin1.refresh_from_db()
        assert admin1.is_active is False

    def test_non_superuser_toggle_allowed(self):
        """REQ-AR-011 Scenario 11.4 — non-superuser toggle by admin succeeds."""
        admin = self._make_admin("toggle-admin", "t@x.com")
        non_super = User.objects.create_user(username="reg-user", password="pass")
        client = Client()
        self._login_admin(client, admin)
        response = client.post(f"/users/{non_super.pk}/toggle/")
        assert response.status_code == 200

        non_super.refresh_from_db()
        assert non_super.is_active is False

    def test_guard_runs_before_atomic(self):
        """REQ-AR-011 Scenario 11.5 — guard rejects BEFORE atomic block opens.

        Verified indirectly: when self-deactivation is rejected, no audit
        row is created (which would only happen inside the atomic block).
        """
        admin = self._make_admin("guard-order", "g@x.com")
        client = Client()
        self._login_admin(client, admin)
        response = client.post(f"/users/{admin.pk}/toggle/")
        assert response.status_code == 400
        assert AuditLog.objects.filter(object_id=admin.pk).count() == 0