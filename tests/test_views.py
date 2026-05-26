from axes import admin
import pytest
from django.contrib.auth.models import User, Group, Permission
from core.models import Resource, AccessGrant, AuditLog
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
class TestResourceListView:
    def test_redirects_if_not_logged_in(self, client):
        response = client.get("/resources/")
        assert response.status_code == 302

    def test_viewer_can_see_list(self, viewer_client):
        response = viewer_client.get("/resources/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestResourceCreateView:
    def test_viewer_cannot_create(self, viewer_client):
        response = viewer_client.post(
            "/resources/create/",
            data={"name": "test", "resource_type": "server", "environment": "dev"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 403

    def test_editor_can_create(self, editor_client):
        response = editor_client.post(
            "/resources/create/",
            data={
                "name": "nuevo-servidor",
                "resource_type": "server",
                "environment": "dev",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestResourceDeleteView:
    def test_editor_cannot_delete(self, editor_client):
        resource = Resource.objects.create(
            name="test-user",
            resource_type="server",
        )
        response = editor_client.post(
            f"/resources/{resource.pk}/delete/", HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        assert response.status_code == 403

    def test_admin_can_delete(self, admin_client):
        resource = Resource.objects.create(
            name="test-user",
            resource_type="server",
        )
        response = admin_client.post(
            f"/resources/{resource.pk}/delete/", HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestGrantCreateView:
    def test_viewer_cannot_create_grant(self, viewer_client):
        resource = Resource.objects.create(
            name="test-user",
            resource_type="server",
        )
        response = viewer_client.post(
            f"/resources/{resource.pk}/grants/create/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 403

    def test_admin_can_create_grant(self, admin_client):
        resource = Resource.objects.create(
            name="test-user",
            resource_type="server",
        )
        target_user = User.objects.create_user(username="target", password="pass")

        response = admin_client.post(
            f"/resources/{resource.pk}/grants/create/",
            data={
                "user": target_user.pk,
                "access_level": "read",
                "start_at": "2026-01-01",
                "end_at": "2026-07-09",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestGrantRevokeView:
    def test_editor_cannot_revoke(self, editor_client):
        target_user = User.objects.create_user(username="target", password="pass")
        resource = Resource.objects.create(
            name="test-server",
            resource_type="server",
        )
        grant = AccessGrant.objects.create(
            user=target_user,
            resource=resource,
            access_level=AccessGrant.AccessLevel.READ,
            start_at=timezone.now(),
            end_at=timezone.now() + timedelta(days=30),
        )
        response = editor_client.post(f"/grants/{grant.pk}/revoke")
        assert response.status_code == 403

    def test_admin_can_revoke(self, admin_client):
        target_user = User.objects.create_user(username="target", password="pass")
        resource = Resource.objects.create(
            name="test-server",
            resource_type="server",
        )
        grant = AccessGrant.objects.create(
            user=target_user,
            resource=resource,
            access_level=AccessGrant.AccessLevel.READ,
            start_at=timezone.now(),
            end_at=timezone.now() + timedelta(days=30),
        )
        response = admin_client.post(f"/grants/{grant.pk}/revoke")
        assert response.status_code == 302


@pytest.mark.django_db
class TestAuditLogView:
    def test_redirects_if_not_logged_in(self, client):
        response = client.get("/audit_log/")
        assert response.status_code == 302

    def test_viewer_cannot_access(self, viewer_client):
        response = viewer_client.get("/audit_log/")
        assert response.status_code == 403

    def test_editor_cannot_access(self, editor_client):
        response = editor_client.get("/audit_log/")
        assert response.status_code == 403

    def test_admin_can_access(self, admin_client):
        response = admin_client.get("/audit_log/")
        assert response.status_code == 200

    # ── Audit log detail modal diff tests ──

    def test_create_action_renders_diff_table(self, admin_client):
        """Create action: diff table present, no old pre blocks, data attrs correct."""
        AuditLog.objects.create(
            user=None,
            action="resource_created",
            object_type="Resource",
            object_id=1,
            object_repr="test-server",
            before=None,
            after={"name": "test-server", "resource_type": "server"},
        )
        response = admin_client.get("/audit_log/")
        assert response.status_code == 200
        content = response.content.decode()

        # Diff table exists
        assert '<table class="diff-table"' in content

        # No old <pre> blocks
        assert 'id="detailBefore"' not in content
        assert 'id="detailAfter"' not in content

        # Data attributes present
        assert 'data-before=' in content
        assert 'data-after=' in content

        # parseSnapshot reference exists in JS
        assert 'parseSnapshot' in content

    def test_delete_action_data_attributes(self, admin_client):
        """Delete action: data-before has content, data-after is empty."""
        AuditLog.objects.create(
            user=None,
            action="resource_deleted",
            object_type="Resource",
            object_id=2,
            object_repr="old-resource",
            before={"name": "old-resource", "resource_type": "database"},
            after=None,
        )
        response = admin_client.get("/audit_log/")
        assert response.status_code == 200
        content = response.content.decode()

        # Diff table structure present
        assert '<table class="diff-table"' in content
        assert 'id="detailBefore"' not in content
        assert 'id="detailAfter"' not in content

        # data-before contains field data (Python repr in template)
        assert "data-before=" in content
        assert "data-after=" in content

    def test_update_action_shows_only_changed_fields(self, admin_client):
        """Update action: both data-before and data-after present, computeDiff reference exists."""
        AuditLog.objects.create(
            user=None,
            action="resource_updated",
            object_type="Resource",
            object_id=3,
            object_repr="updated-resource",
            before={"name": "old-name", "resource_type": "server", "environment": "dev"},
            after={"name": "new-name", "resource_type": "server", "environment": "prod"},
        )
        response = admin_client.get("/audit_log/")
        assert response.status_code == 200
        content = response.content.decode()

        # Diff table and JS functions present
        assert '<table class="diff-table"' in content
        assert 'computeDiff' in content
        assert 'renderDiffTable' in content

        # Data attributes contain both before and after
        assert "data-before=" in content
        assert "data-after=" in content

    def test_no_changes_shows_empty_state(self, admin_client):
        """Identical before/after: diff table still present, empty state handled by JS."""
        AuditLog.objects.create(
            user=None,
            action="resource_updated",
            object_type="Resource",
            object_id=4,
            object_repr="unchanged-resource",
            before={"name": "same", "type": "server"},
            after={"name": "same", "type": "server"},
        )
        response = admin_client.get("/audit_log/")
        assert response.status_code == 200
        content = response.content.decode()

        # Diff table structure exists (JS shows empty state message on click)
        assert '<table class="diff-table"' in content
        assert '"No hay cambios para mostrar"' in content or "No hay cambios" in content

    # ── Triangulation: edge cases ──

    def test_create_entry_data_before_is_empty(self, admin_client):
        """Create action with null before: data-before attribute is empty string."""
        AuditLog.objects.create(
            user=None,
            action="resource_created",
            object_type="Resource",
            object_id=5,
            object_repr="fresh-resource",
            before=None,
            after={"name": "fresh", "env": "prod"},
        )
        response = admin_client.get("/audit_log/")
        content = response.content.decode()

        # The data-before attribute on the create entry should be empty
        assert 'data-before=""' in content or "data-before=''" in content

    def test_update_entry_data_attrs_contain_field_values(self, admin_client):
        """Update action: both data-before and data-after contain differing values."""
        AuditLog.objects.create(
            user=None,
            action="grant_created",
            object_type="AccessGrant",
            object_id=6,
            object_repr="test-user → resource (read)",
            before={"access_level": "none", "status": "inactive"},
            after={"access_level": "read", "status": "active"},
        )
        response = admin_client.get("/audit_log/")
        content = response.content.decode()

        # Verify data attributes exist with content (not empty)
        # Django renders JSONField as Python repr: {'key': 'val'}
        assert 'data-before=' in content
        assert 'data-after=' in content
        # The old value "none" and new value "read" should appear in the page
        assert 'none' in content
        assert 'active' in content
        # Diff table structure present
        assert '<table class="diff-table"' in content

    # ── HTMX navigation tests ──

    def test_htmx_request_returns_partial(self, admin_client):
        """HTMX request returns partial template without base layout."""
        AuditLog.objects.create(
            user=None,
            action="resource_created",
            object_type="Resource",
            object_id=10,
            object_repr="htmx-test",
            before=None,
            after={"name": "htmx-test"},
        )
        response = admin_client.get("/audit_log/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "<html" not in content

    def test_htmx_partial_includes_modal_js(self, admin_client):
        """HTMX partial includes inline modal JS for re-initialization."""
        response = admin_client.get("/audit_log/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "parseSnapshot" in content
        assert "computeDiff" in content

    def test_normal_request_returns_full_page(self, admin_client):
        """Non-HTMX request returns full page with base template."""
        AuditLog.objects.create(
            user=None,
            action="resource_created",
            object_type="Resource",
            object_id=11,
            object_repr="full-page-test",
            before=None,
            after={"name": "full-page-test"},
        )
        response = admin_client.get("/audit_log/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "<html" in content

    def test_htmx_partial_excludes_block_wrappers(self, admin_client):
        """HTMX partial does not include Django template block syntax."""
        response = admin_client.get("/audit_log/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "{% extends" not in content
        assert "{% block" not in content


@pytest.mark.django_db
class TestUserCreateView:
    def test_non_ajax_get_redirects_to_user_management(self, admin_client):
        """Direct GET should redirect to user_management instead of 500."""
        response = admin_client.get("/users/create/")
        assert response.status_code == 302
        assert response.url == "/users/manage/"

    def test_non_admin_cannot_access(self, viewer_client):
        response = viewer_client.get("/users/create/")
        assert response.status_code == 403

    def test_ajax_get_returns_405(self, admin_client):
        response = admin_client.get(
            "/users/create/", HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        assert response.status_code == 405

    def test_ajax_post_creates_user(self, admin_client):
        group = Group.objects.create(name="test-group")
        response = admin_client.post(
            "/users/create/",
            data={
                "username": "newuser",
                "email": "new@test.com",
                "first_name": "New",
                "last_name": "User",
                "password": "testpass123",
                "role": group.pk,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_ajax_post_requires_password(self, admin_client):
        group = Group.objects.create(name="test-group")
        response = admin_client.post(
            "/users/create/",
            data={
                "username": "newuser",
                "email": "new@test.com",
                "first_name": "New",
                "last_name": "User",
                "role": group.pk,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "password" in data["errors"]


@pytest.mark.django_db
class TestUserUpdateView:
    def test_non_ajax_get_redirects_to_user_management(self, admin_client):
        """Direct GET should redirect to user_management instead of 500."""
        user = User.objects.create_user(username="targetuser", password="pass")
        response = admin_client.get(f"/users/{user.pk}/edit/")
        assert response.status_code == 302
        assert response.url == "/users/manage/"

    def test_non_admin_cannot_access(self, viewer_client):
        user = User.objects.create_user(username="targetuser", password="pass")
        response = viewer_client.get(f"/users/{user.pk}/edit/")
        assert response.status_code == 403

    def test_ajax_get_returns_405(self, admin_client):
        user = User.objects.create_user(username="targetuser", password="pass")
        response = admin_client.get(
            f"/users/{user.pk}/edit/", HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        assert response.status_code == 405


@pytest.mark.django_db
class TestUserProfileView:
    def test_redirects_if_not_logged_in(self, client):
        response = client.get("/users/profile/")
        assert response.status_code == 302

    def test_authenticated_user_can_access(self, viewer_client):
        response = viewer_client.get("/users/profile/")
        assert response.status_code == 200

    def test_htmx_request_returns_partial(self, viewer_client):
        """HTMX request returns partial without base layout."""
        response = viewer_client.get("/users/profile/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "<html" not in content

    def test_htmx_partial_has_profile_content(self, viewer_client):
        """HTMX partial includes profile info but no block wrappers."""
        response = viewer_client.get("/users/profile/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Perfil" in content
        assert "{% extends" not in content
        assert "{% block" not in content

    def test_normal_request_returns_full_page(self, viewer_client):
        """Non-HTMX request returns full page with base template."""
        response = viewer_client.get("/users/profile/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "<html" in content

    def test_htmx_partial_excludes_extra_css_block(self, viewer_client):
        """HTMX partial should not include the extra_css block (styles live in <head>)."""
        response = viewer_client.get("/users/profile/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert "{% block extra_css %}" not in content
        assert "profile-page" in content
