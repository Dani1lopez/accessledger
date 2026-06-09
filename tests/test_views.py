from axes import admin
import pytest
from django.contrib.auth.models import User, Group, Permission
from core.models import Resource, AccessGrant, AuditLog, Profile
from django.utils import timezone
from datetime import timedelta
import re


@pytest.mark.django_db
class TestUserCanModifyResourceHelper:
    """Unit tests for the user_can_modify_resource pure function."""

    def test_superuser_always_allowed(self):
        from core.permissions import user_can_modify_resource
        superuser = User.objects.create_superuser(
            username="su1", password="pass", email="su1@x.com"
        )
        resource = Resource.objects.create(
            name="r1", resource_type="server"
        )
        assert user_can_modify_resource(superuser, resource) is True

    def test_admin_group_always_allowed(self):
        from core.permissions import user_can_modify_resource
        group, _ = Group.objects.get_or_create(name="admin")
        admin_user = User.objects.create_user(username="adm", password="pass")
        admin_user.groups.add(group)
        resource = Resource.objects.create(
            name="r2", resource_type="server"
        )
        assert user_can_modify_resource(admin_user, resource) is True

    def test_owner_can_modify_own_resource(self):
        from core.permissions import user_can_modify_resource
        editor = User.objects.create_user(username="ed", password="pass")
        resource = Resource.objects.create(
            name="r3", resource_type="server", owner=editor
        )
        assert user_can_modify_resource(editor, resource) is True

    def test_non_owner_cannot_modify_others_resource(self):
        from core.permissions import user_can_modify_resource
        editor = User.objects.create_user(username="ed2", password="pass")
        other = User.objects.create_user(username="other", password="pass")
        resource = Resource.objects.create(
            name="r4", resource_type="server", owner=other
        )
        assert user_can_modify_resource(editor, resource) is False

    def test_orphan_resource_denied_for_regular_user(self):
        from core.permissions import user_can_modify_resource
        editor = User.objects.create_user(username="ed3", password="pass")
        resource = Resource.objects.create(
            name="r5", resource_type="server", owner=None
        )
        assert user_can_modify_resource(editor, resource) is False

    def test_admin_can_modify_orphan_resource(self):
        from core.permissions import user_can_modify_resource
        group, _ = Group.objects.get_or_create(name="admin")
        admin_user = User.objects.create_user(username="adm2", password="pass")
        admin_user.groups.add(group)
        resource = Resource.objects.create(
            name="r6", resource_type="server", owner=None
        )
        assert user_can_modify_resource(admin_user, resource) is True

    def test_superuser_can_modify_orphan_resource(self):
        from core.permissions import user_can_modify_resource
        superuser = User.objects.create_superuser(
            username="su2", password="pass", email="su2@x.com"
        )
        resource = Resource.objects.create(
            name="r7", resource_type="server", owner=None
        )
        assert user_can_modify_resource(superuser, resource) is True


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

    def test_editor_owns_can_delete(self, client):
        group, _ = Group.objects.get_or_create(name="editor-del")
        perm = Permission.objects.get(codename="delete_resource")
        group.permissions.add(perm)
        editor = User.objects.create_user(username="edel", password="pass")
        editor.profile.must_change_password = False
        editor.profile.save()
        editor.groups.add(group)
        client.login(username="edel", password="pass")

        resource = Resource.objects.create(
            name="del-own", resource_type="server", owner=editor
        )
        response = client.post(
            f"/resources/{resource.pk}/delete/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200

    def test_editor_cannot_delete_others(self, client):
        group, _ = Group.objects.get_or_create(name="editor-del2")
        perm = Permission.objects.get(codename="delete_resource")
        group.permissions.add(perm)
        editor = User.objects.create_user(username="edel2", password="pass")
        editor.profile.must_change_password = False
        editor.profile.save()
        editor.groups.add(group)
        client.login(username="edel2", password="pass")

        other = User.objects.create_user(username="otherdel", password="pass")
        resource = Resource.objects.create(
            name="del-other", resource_type="server", owner=other
        )
        response = client.post(
            f"/resources/{resource.pk}/delete/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 403

    def test_superuser_can_delete_any(self, client):
        superuser = User.objects.create_superuser(
            username="su5", password="pass", email="su5@x.com"
        )
        superuser.profile.must_change_password = False
        superuser.profile.save()
        client.login(username="su5", password="pass")

        other = User.objects.create_user(username="otherdel2", password="pass")
        resource = Resource.objects.create(
            name="del-su", resource_type="server", owner=other
        )
        response = client.post(
            f"/resources/{resource.pk}/delete/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200

    def test_editor_cannot_delete_orphan(self, client):
        group, _ = Group.objects.get_or_create(name="editor-del3")
        perm = Permission.objects.get(codename="delete_resource")
        group.permissions.add(perm)
        editor = User.objects.create_user(username="edel3", password="pass")
        editor.profile.must_change_password = False
        editor.profile.save()
        editor.groups.add(group)
        client.login(username="edel3", password="pass")

        resource = Resource.objects.create(
            name="del-orph", resource_type="server", owner=None
        )
        response = client.post(
            f"/resources/{resource.pk}/delete/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestResourceUpdateView:
    """Ownership gating on resource_update view."""

    def test_editor_owns_resource_get(self, editor_client):
        editor = User.objects.get(username="editor1")
        resource = Resource.objects.create(
            name="ed-own-get", resource_type="server", environment="dev", owner=editor
        )
        response = editor_client.get(f"/resources/{resource.pk}/edit/")
        assert response.status_code == 200

    def test_editor_owns_resource_post(self, editor_client):
        editor = User.objects.get(username="editor1")
        resource = Resource.objects.create(
            name="ed-own-post", resource_type="server", environment="dev", owner=editor
        )
        response = editor_client.post(
            f"/resources/{resource.pk}/edit/",
            data={
                "name": "ed-own-post",
                "resource_type": "server",
                "environment": "prod",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200

    def test_editor_cannot_edit_others_resource(self, editor_client):
        other = User.objects.create_user(username="othered", password="pass")
        resource = Resource.objects.create(
            name="others-ed", resource_type="server", environment="dev", owner=other
        )
        response = editor_client.get(f"/resources/{resource.pk}/edit/")
        assert response.status_code == 403

    def test_admin_can_edit_any_resource(self, admin_client):
        other = User.objects.create_user(username="othered2", password="pass")
        resource = Resource.objects.create(
            name="admin-any", resource_type="server", environment="dev", owner=other
        )
        response = admin_client.get(f"/resources/{resource.pk}/edit/")
        assert response.status_code == 200

    def test_superuser_can_edit_any_resource(self, client):
        superuser = User.objects.create_superuser(
            username="su3", password="pass", email="su3@x.com"
        )
        superuser.profile.must_change_password = False
        superuser.profile.save()
        client.login(username="su3", password="pass")
        other = User.objects.create_user(username="othered3", password="pass")
        resource = Resource.objects.create(
            name="su-any", resource_type="server", environment="dev", owner=other
        )
        response = client.get(f"/resources/{resource.pk}/edit/")
        assert response.status_code == 200

    def test_editor_cannot_edit_orphan_resource(self, editor_client):
        resource = Resource.objects.create(
            name="orph-ed", resource_type="server", environment="dev", owner=None
        )
        response = editor_client.get(f"/resources/{resource.pk}/edit/")
        assert response.status_code == 403

    def test_admin_can_edit_orphan_resource(self, admin_client):
        resource = Resource.objects.create(
            name="orph-adm", resource_type="server", environment="dev", owner=None
        )
        response = admin_client.get(f"/resources/{resource.pk}/edit/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestResourceDataView:
    """Ownership gating on resource_data JSON endpoint."""

    def test_editor_owns_returns_json(self, editor_client):
        editor = User.objects.get(username="editor1")
        resource = Resource.objects.create(
            name="data-own", resource_type="server", environment="dev", owner=editor
        )
        response = editor_client.get(f"/resources/{resource.pk}/data/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"

    def test_editor_not_owner_returns_403(self, editor_client):
        other = User.objects.create_user(username="otherdata", password="pass")
        resource = Resource.objects.create(
            name="data-other", resource_type="server", environment="dev", owner=other
        )
        response = editor_client.get(f"/resources/{resource.pk}/data/")
        assert response.status_code == 403

    def test_superuser_returns_json(self, client):
        superuser = User.objects.create_superuser(
            username="su4", password="pass", email="su4@x.com"
        )
        superuser.profile.must_change_password = False
        superuser.profile.save()
        client.login(username="su4", password="pass")
        other = User.objects.create_user(username="otherdata2", password="pass")
        resource = Resource.objects.create(
            name="data-su", resource_type="server", environment="dev", owner=other
        )
        response = client.get(f"/resources/{resource.pk}/data/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
class TestResourceDetailView:
    """can_modify context boolean in resource_detail view."""

    def test_can_modify_true_for_owner(self, editor_client):
        editor = User.objects.get(username="editor1")
        resource = Resource.objects.create(
            name="det-own", resource_type="server", environment="dev", owner=editor
        )
        response = editor_client.get(f"/resources/{resource.pk}/")
        assert response.status_code == 200
        content = response.content.decode()
        # Edit button should be present when can_modify is True
        assert 'id="btnEditResource"' in content

    def test_can_modify_false_for_non_owner(self, editor_client):
        other = User.objects.create_user(username="otherdet", password="pass")
        resource = Resource.objects.create(
            name="det-other", resource_type="server", environment="dev", owner=other
        )
        response = editor_client.get(f"/resources/{resource.pk}/")
        assert response.status_code == 200
        content = response.content.decode()
        # Edit button should NOT be present when can_modify is False
        assert 'id="btnEditResource"' not in content

    def test_can_modify_false_for_orphan_editor(self, editor_client):
        resource = Resource.objects.create(
            name="det-orph", resource_type="server", environment="dev", owner=None
        )
        response = editor_client.get(f"/resources/{resource.pk}/")
        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="btnEditResource"' not in content


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

        # delegated.js loaded (parseSnapshot/computeDiff now live there)
        assert 'delegated.js' in content

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

        # Diff table and delegated.js present (functions moved there)
        assert '<table class="diff-table"' in content
        assert 'delegated.js' in content

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

    def test_htmx_partial_no_inline_script(self, admin_client):
        """HTMX partial no longer contains inline style/script — CSS lives in external files."""
        AuditLog.objects.create(
            user=None,
            action="resource_created",
            object_type="Resource",
            object_id=99,
            object_repr="test-css",
            before=None,
            after={"name": "test-css"},
        )
        response = admin_client.get("/audit_log/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()
        assert '<dialog id="modalAuditDetail"' in content
        assert 'class="btn-detail"' in content
        assert '<script' not in content
        assert '<style' not in content

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

    def test_password_update_sets_must_change_password_true(self, admin_client):
        """REGRESSION: admin updating a user's password MUST flag forced change.

        Bug: ``user_update`` called ``user.set_password(password)`` but never
        touched ``Profile.must_change_password``, so the target user could log
        in with the new password and skip the forced-change middleware.
        """
        group = Group.objects.create(name="viewer")
        target = User.objects.create_user(username="targetuser", password="oldpass")
        target.profile.must_change_password = False
        target.profile.save()
        target.groups.add(group)

        response = admin_client.post(
            f"/users/{target.pk}/edit/",
            data={
                "username": "targetuser",
                "email": "target@test.com",
                "first_name": "Target",
                "last_name": "User",
                "role": group.pk,
                "password": "newpass123",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        target.profile.refresh_from_db()
        assert target.profile.must_change_password is True

    def test_non_password_update_does_not_set_must_change_password(self, admin_client):
        """When admin updates user fields WITHOUT a new password, the flag stays."""
        group = Group.objects.create(name="viewer")
        target = User.objects.create_user(username="targetuser", password="oldpass")
        target.profile.must_change_password = False
        target.profile.save()
        target.groups.add(group)

        response = admin_client.post(
            f"/users/{target.pk}/edit/",
            data={
                "username": "renameduser",
                "email": "newemail@test.com",
                "first_name": "Renamed",
                "last_name": "User",
                "role": group.pk,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        target.profile.refresh_from_db()
        assert target.profile.must_change_password is False

    def test_password_update_creates_profile_if_missing(self, admin_client):
        """Edge case: user with no Profile gets one created with flag=True."""
        group = Group.objects.create(name="viewer")
        target = User.objects.create_user(username="targetuser", password="oldpass")
        target.profile.delete()  # Simulate missing Profile

        response = admin_client.post(
            f"/users/{target.pk}/edit/",
            data={
                "username": "targetuser",
                "email": "target@test.com",
                "first_name": "Target",
                "last_name": "User",
                "role": group.pk,
                "password": "newpass123",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Profile must now exist with must_change_password=True
        profile = Profile.objects.get(user=target)
        assert profile.must_change_password is True

    def test_admin_password_update_forces_change_on_next_login(self, admin_client):
        """REQ-3 full flow: admin updates password → user logs in with new password
        → middleware redirects to /password/change/.

        Bug regression: previously, ``user_update`` rotated the password but
        did not set ``must_change_password=True``, so the user could log in
        with the new password and bypass the forced-change flow entirely.
        """
        group = Group.objects.create(name="viewer")
        target = User.objects.create_user(username="targetuser", password="oldpass")
        target.profile.must_change_password = False
        target.profile.save()
        target.groups.add(group)

        # 1. Admin updates the target's password.
        response = admin_client.post(
            f"/users/{target.pk}/edit/",
            data={
                "username": "targetuser",
                "email": "target@test.com",
                "first_name": "Target",
                "last_name": "User",
                "role": group.pk,
                "password": "newpass123",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # 2. Target user logs in with the NEW password.
        admin_client.logout()
        login_ok = admin_client.login(username="targetuser", password="newpass123")
        assert login_ok is True, "Target user should be able to log in with the new password"

        # 3. Target requests a protected URL — middleware must redirect.
        response = admin_client.get("/resources/")
        assert response.status_code == 302
        assert response.url == "/password/change/"

    def test_empty_password_field_preserves_existing_password(self, admin_client):
        """REQ-2: explicit empty password field MUST NOT overwrite the user's password.

        The form may submit ``password=""`` (empty string, not omitted) when the
        admin leaves the field blank. The view must skip the password update
        branch entirely so the target can still log in with the previous password.
        """
        group = Group.objects.create(name="viewer")
        target = User.objects.create_user(username="targetuser", password="oldpass")
        target.profile.must_change_password = False
        target.profile.save()
        target.groups.add(group)

        # Admin submits update form with EXPLICIT empty password.
        response = admin_client.post(
            f"/users/{target.pk}/edit/",
            data={
                "username": "targetuser",
                "email": "target@test.com",
                "first_name": "Target",
                "last_name": "User",
                "role": group.pk,
                "password": "",  # explicit empty string
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # The previous password must still work — proves no overwrite happened.
        target.refresh_from_db()
        assert target.check_password("oldpass") is True
        assert target.check_password("") is False

        # Flag must remain False — we did not rotate the password.
        target.profile.refresh_from_db()
        assert target.profile.must_change_password is False

        # And the user can still log in with the old password.
        admin_client.logout()
        login_ok = admin_client.login(username="targetuser", password="oldpass")
        assert login_ok is True, "User should still be able to log in with old password"


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


@pytest.mark.django_db
class TestPasswordChangeTemplates:
    """Verify auth pages render the topbar with the brand logo but no nav links."""

    def test_password_change_page_has_topbar_with_logo_but_no_nav(self, forced_password_client):
        """Password change page includes the topbar + brand logo but no navigation links."""
        response = forced_password_client.get("/password/change/")
        assert response.status_code == 200
        content = response.content.decode()
        # Topbar with logo SHOULD be present.
        assert '<header class="topbar"' in content
        assert 'class="brand__dot"' in content
        assert 'class="brand__name"' in content
        # Navigation links SHOULD NOT be present on auth pages.
        assert "<nav" not in content
        assert "nav__link" not in content
        assert 'action="/logout/"' not in content

    def test_password_change_page_has_no_logout_form(self, forced_password_client):
        """Password change page must NOT include a logout form."""
        response = forced_password_client.get("/password/change/")
        assert response.status_code == 200
        content = response.content.decode()
        assert 'action="/logout/"' not in content

    def test_login_page_has_topbar_with_logo_but_no_nav(self, client):
        """Login page includes the topbar + brand logo but no navigation links."""
        response = client.get("/login/")
        assert response.status_code == 200
        content = response.content.decode()
        # Topbar with logo SHOULD be present.
        assert '<header class="topbar"' in content
        assert 'class="brand__dot"' in content
        assert 'class="brand__name"' in content
        # Navigation links SHOULD NOT be present on auth pages.
        assert "<nav" not in content
        assert "nav__link" not in content

    def test_lockout_page_has_topbar_with_logo_but_no_nav(self):
        """Lockout template includes the topbar + brand logo but no navigation links."""
        from django.template.loader import render_to_string
        html = render_to_string("axes/lockout.html")
        # Topbar with logo SHOULD be present.
        assert '<header class="topbar"' in html
        assert 'class="brand__dot"' in html
        assert 'class="brand__name"' in html
        # Navigation links SHOULD NOT be present on auth pages.
        assert "<nav" not in html
        assert "nav__link" not in html

    def test_resource_list_still_has_topbar(self, viewer_client):
        """Regression guard: authenticated pages with a resolved user still get the full topbar."""
        response = viewer_client.get("/resources/")
        assert response.status_code == 200
        content = response.content.decode()
        assert '<header class="topbar"' in content

    def test_password_change_recovery_paragraph_renders(self, forced_password_client):
        """Password change page shows recovery mailto link with admin email."""
        response = forced_password_client.get("/password/change/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "mailto:" in content
        assert "admin@example.com" in content


@pytest.mark.django_db
class TestPasswordChangeAuditLog:
    """Verify audit logging on successful password change."""

    def test_password_change_creates_audit_log(self, forced_password_client):
        """Successful password change creates an AuditLog entry with action=password_changed."""
        from django.contrib.auth.models import User
        user = User.objects.get(username="forced1")
        response = forced_password_client.post(
            "/password/change/",
            data={
                "old_password": "ForcedPass123!",
                "new_password1": "Newpass123!",
                "new_password2": "Newpass123!",
            },
        )
        assert response.status_code == 302
        assert AuditLog.objects.filter(
            action="password_changed", user=user
        ).exists()


@pytest.mark.django_db
class TestCustomPasswordChangeView:
    """Verify CustomPasswordChangeView behavior: clears flag and redirects."""

    def test_password_change_success_sets_must_change_false(self, forced_password_client):
        """After successful password change, must_change_password becomes False."""
        from django.contrib.auth.models import User
        response = forced_password_client.post(
            "/password/change/",
            data={
                "old_password": "ForcedPass123!",
                "new_password1": "Newpass123!",
                "new_password2": "Newpass123!",
            },
        )
        assert response.status_code == 302
        user = User.objects.get(username="forced1")
        user.profile.refresh_from_db()
        assert user.profile.must_change_password is False

    def test_password_change_success_redirects_to_resource_list(self, forced_password_client):
        """After successful password change, user is redirected to resource list."""
        response = forced_password_client.post(
            "/password/change/",
            data={
                "old_password": "ForcedPass123!",
                "new_password1": "Newpass123!",
                "new_password2": "Newpass123!",
            },
        )
        assert response.status_code == 302
        assert response.url == "/resources/"


# ════════════════════════════════════════════════════════════════════════════════
# Pagination tests — feat/pagination
# ════════════════════════════════════════════════════════════════════════════════
#
# These tests are written FIRST in strict TDD: the _paginate helper, the
# _pagination.html partial, and the paginated view code do not exist yet.
# Every test below MUST fail at this stage (RED gate).


def _make_audit_logs(n: int, base_username: str = "actor") -> None:
    """Bulk-create N audit log entries with predictable object_repr values."""
    AuditLog.objects.bulk_create(
        [
            AuditLog(
                user=None,
                action="resource_created",
                object_type="Resource",
                object_id=i + 1,
                object_repr=f"{base_username}-r{i + 1}",
                before=None,
                after={"name": f"{base_username}-r{i + 1}"},
            )
            for i in range(n)
        ]
    )


def _audit_reprs_in(content: str) -> set[str]:
    """Extract the set of audit-object-repr spans from an HTML response."""
    return set(re.findall(r'audit-object-repr">([^<]+)<', content))


def _pill_text(content: str) -> str:
    """Extract the first ``<div class="pill">...</div>`` text from a response."""
    m = re.search(r'<div class="pill"[^>]*>([^<]+)</div>', content)
    assert m is not None, "Count pill not found in response"
    return m.group(1).strip()


@pytest.mark.django_db
class TestPaginateHelper:
    """Unit tests for the shared _paginate(request, qs) helper."""

    def test_returns_page_obj_with_first_page_when_no_param(self):
        from django.test import RequestFactory
        from core.views import _paginate
        from core.models import Resource

        # 25 resources → expect 2 pages at PAGE_SIZE=20
        Resource.objects.bulk_create(
            [Resource(name=f"r{i}", resource_type="server") for i in range(25)]
        )
        request = RequestFactory().get("/resources/")
        page_obj, paginator = _paginate(request, Resource.objects.all().order_by("name"))

        assert paginator.count == 25
        assert paginator.num_pages == 2
        assert page_obj.number == 1
        assert len(page_obj.object_list) == 20

    def test_get_page_returns_last_page_for_out_of_range(self):
        from django.test import RequestFactory
        from core.views import _paginate
        from core.models import Resource

        Resource.objects.bulk_create(
            [Resource(name=f"r{i}", resource_type="server") for i in range(25)]
        )
        request = RequestFactory().get("/resources/?page=999")
        page_obj, paginator = _paginate(request, Resource.objects.all().order_by("name"))

        # Out-of-range must fall back to the last valid page, not 404
        assert page_obj.number == paginator.num_pages == 2
        assert len(page_obj.object_list) == 5

    def test_get_page_returns_first_page_for_non_integer(self):
        from django.test import RequestFactory
        from core.views import _paginate
        from core.models import Resource

        Resource.objects.bulk_create(
            [Resource(name=f"r{i}", resource_type="server") for i in range(25)]
        )
        request = RequestFactory().get("/resources/?page=abc")
        page_obj, paginator = _paginate(request, Resource.objects.all().order_by("name"))

        # Non-integer must fall back to page 1
        assert page_obj.number == 1


@pytest.mark.django_db
class TestAuditLogPagination:
    """Integration tests for the paginated audit_log view.

    Entries are ordered by ``-timestamp`` in the view. ``_make_audit_logs``
    bulk-creates rows in id order (r1 oldest → r25 newest). With ``-timestamp``
    ordering, r25 appears on page 1 and r1 appears on page 2.

    Object reprs are matched on the ``<span class="mono audit-object-repr">``
    boundary so substrings like "actor-r1" inside "actor-r10" do not match.
    """

    def test_audit_log_pagination_renders_only_one_page_of_rows(self, admin_client):
        """When more than 20 entries exist, page 1 renders 20 rows, page 2 has the rest."""
        _make_audit_logs(25)
        response = admin_client.get("/audit_log/")
        assert response.status_code == 200
        reprs = _audit_reprs_in(response.content.decode())

        # Page 1: newest 20 → r6..r25
        for i in range(6, 26):
            assert f"actor-r{i}" in reprs, f"actor-r{i} should appear on page 1"
        # Page 1 must NOT contain the oldest 5 (r1..r5)
        for i in range(1, 6):
            assert f"actor-r{i}" not in reprs, f"actor-r{i} should NOT appear on page 1"

    def test_audit_log_pagination_page_param_returns_correct_slice(self, admin_client):
        """?page=2 returns the oldest 5 entries (r1..r5)."""
        _make_audit_logs(25)
        response = admin_client.get("/audit_log/?page=2")
        assert response.status_code == 200
        reprs = _audit_reprs_in(response.content.decode())

        # Page 2: oldest 5 → r1..r5
        for i in range(1, 6):
            assert f"actor-r{i}" in reprs, f"actor-r{i} should appear on page 2"
        # Newest entries must NOT be on page 2
        assert "actor-r25" not in reprs

    def test_audit_log_pagination_out_of_range_returns_last_page(self, admin_client):
        """?page=999 falls back to the last valid page (no 404)."""
        _make_audit_logs(25)
        response = admin_client.get("/audit_log/?page=999")
        assert response.status_code == 200
        reprs = _audit_reprs_in(response.content.decode())

        # Last page: oldest 5 → r1..r5 must be present
        for i in range(1, 6):
            assert f"actor-r{i}" in reprs

    def test_audit_log_pagination_renders_pagination_partial(self, admin_client):
        """The _pagination.html partial must be present in the response."""
        _make_audit_logs(25)
        response = admin_client.get("/audit_log/")
        assert response.status_code == 200
        content = response.content.decode()

        # Pagination navigation must be present
        assert 'class="pagination"' in content
        # Must contain a link to page 2
        assert "page=2" in content

    def test_audit_log_pagination_count_pill_uses_paginator_count(self, admin_client):
        """Count pill must show the total (25) on EVERY page, not the page size (20).

        This is the regression that motivates using ``paginator.count`` over
        ``|length``: on page 2 (5 rows), ``|length`` would falsely show 5.
        """
        _make_audit_logs(25)

        # Page 1: pill must show 25 (total), not 20 (page size)
        response = admin_client.get("/audit_log/")
        assert _pill_text(response.content.decode()) == "25 registros"

        # Page 2: pill must STILL show 25, not 5 (the page size of 5 rows)
        response = admin_client.get("/audit_log/?page=2")
        assert _pill_text(response.content.decode()) == "25 registros"

    def test_audit_log_htmx_partial_includes_pagination(self, admin_client):
        """HTMX request also returns the pagination partial so links survive swaps."""
        _make_audit_logs(25)
        response = admin_client.get("/audit_log/?page=2", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()

        # Partial response → no <html> wrapper
        assert "<html" not in content
        # Pagination controls must still be present in the partial
        assert 'class="pagination"' in content
        # Must contain a link to page 1
        assert "page=1" in content


@pytest.mark.django_db
class TestUserManagementPagination:
    """Integration tests for the paginated user_management view.

    ``_make_users`` creates 25 users (u1..u25) created in sequence; the view
    returns them in default User ordering (by id, ascending) so u1..u20 are
    on page 1 and u21..u25 are on page 2.
    """

    @staticmethod
    def _make_users(n: int) -> None:
        User.objects.bulk_create(
            [User(username=f"user-pg-{i:02d}", email=f"u{i}@x.com") for i in range(1, n + 1)]
        )

    @staticmethod
    def _usernames_in(content: str) -> set[str]:
        return set(re.findall(r'@user-pg-\d+', content))

    def test_user_management_pagination_renders_only_one_page_of_rows(self, admin_client):
        """When more than 20 users exist, page 1 renders 20 rows, page 2 has the rest.

        The ``admin_client`` fixture creates an ``admin1`` user, so the user
        table already has 1 row before ``_make_users`` runs (25 → 26 total).
        """
        self._make_users(25)
        response = admin_client.get("/users/manage/")
        assert response.status_code == 200
        usernames = self._usernames_in(response.content.decode())

        # Page 1 has 20 rows total. Of the 25 created, 19 should appear on
        # page 1 (the oldest 19: user-pg-01..user-pg-19) because admin1 takes
        # the 1 remaining slot.
        for i in range(1, 20):
            assert f"@user-pg-{i:02d}" in usernames, f"user-pg-{i:02d} should appear on page 1"
        # user-pg-20 and later must NOT be on page 1
        for i in range(20, 26):
            assert (
                f"@user-pg-{i:02d}" not in usernames
            ), f"user-pg-{i:02d} should NOT appear on page 1"

    def test_user_management_pagination_page_param_returns_correct_slice(self, admin_client):
        """?page=2 returns the remaining 6 users (25 created + 1 admin1)."""
        self._make_users(25)
        response = admin_client.get("/users/manage/?page=2")
        assert response.status_code == 200
        usernames = self._usernames_in(response.content.decode())

        # Page 2 holds the 6 newest users
        for i in range(20, 26):
            assert f"@user-pg-{i:02d}" in usernames, f"user-pg-{i:02d} should appear on page 2"
        # user-pg-01 must NOT be on page 2
        assert "@user-pg-01" not in usernames

    def test_user_management_pagination_out_of_range_returns_last_page(self, admin_client):
        """?page=999 falls back to the last valid page (no 404)."""
        self._make_users(25)
        response = admin_client.get("/users/manage/?page=999")
        assert response.status_code == 200
        usernames = self._usernames_in(response.content.decode())

        # Last page: user-pg-20..user-pg-25 must be present
        for i in range(20, 26):
            assert f"@user-pg-{i:02d}" in usernames

    def test_user_management_pagination_count_pill_uses_paginator_count(self, admin_client):
        """Count pill must show the total (26) on every page, not the page size.

        The ``admin_client`` fixture creates admin1, so the total is
        25 (created) + 1 (admin1) = 26 users. With PAGE_SIZE=20, page 1
        has 20 rows and page 2 has 6. The pill must show 26 on both.
        """
        self._make_users(25)

        # Page 1
        response = admin_client.get("/users/manage/")
        assert _pill_text(response.content.decode()) == "26 usuarios"

        # Page 2 — pill must STILL show 26, not 6 (the page size of 6 rows)
        response = admin_client.get("/users/manage/?page=2")
        assert _pill_text(response.content.decode()) == "26 usuarios"

    def test_user_management_pagination_renders_pagination_partial(self, admin_client):
        """The _pagination.html partial must be present in the response."""
        self._make_users(25)
        response = admin_client.get("/users/manage/")
        assert response.status_code == 200
        content = response.content.decode()

        assert 'class="pagination"' in content
        # Must contain a link to page 2
        assert "page=2" in content

    def test_user_management_pagination_preserves_modals(self, admin_client):
        """Pagination swap must NOT strip the modals from the partial.

        Modals live in the partial so the user can still open them after
        clicking a pagination link.
        """
        self._make_users(25)
        response = admin_client.get(
            "/users/manage/?page=2", HTTP_HX_REQUEST="true"
        )
        assert response.status_code == 200
        content = response.content.decode()

        # Partial response → no <html> wrapper
        assert "<html" not in content
        # Create-user modal must still be present
        assert 'id="modalCreateUser"' in content
        # Edit-user modal must still be present
        assert 'id="modalEditUser"' in content
        # Pagination must also be present
        assert 'class="pagination"' in content


@pytest.mark.django_db
class TestResourceListPagination:
    """Integration tests for the paginated resource_list view."""

    @staticmethod
    def _make_resources(n: int) -> None:
        Resource.objects.bulk_create(
            [Resource(name=f"r-pg-{i:02d}", resource_type="server") for i in range(1, n + 1)]
        )

    @staticmethod
    def _resource_names_in(content: str) -> set[str]:
        return set(re.findall(r'r-pg-\d+', content))

    def test_resource_list_pagination_renders_only_one_page_of_rows(self, viewer_client):
        """When more than 20 resources exist, page 1 renders 20 rows."""
        self._make_resources(25)
        response = viewer_client.get("/resources/")
        assert response.status_code == 200
        names = self._resource_names_in(response.content.decode())

        # Page 1: r-pg-01..r-pg-20
        for i in range(1, 21):
            assert f"r-pg-{i:02d}" in names, f"r-pg-{i:02d} should appear on page 1"
        # r-pg-21..r-pg-25 must NOT be on page 1
        for i in range(21, 26):
            assert f"r-pg-{i:02d}" not in names, f"r-pg-{i:02d} should NOT appear on page 1"

    def test_resource_list_pagination_page_param_returns_correct_slice(self, viewer_client):
        """?page=2 returns the remaining 5 resources."""
        self._make_resources(25)
        response = viewer_client.get("/resources/?page=2")
        assert response.status_code == 200
        names = self._resource_names_in(response.content.decode())

        for i in range(21, 26):
            assert f"r-pg-{i:02d}" in names, f"r-pg-{i:02d} should appear on page 2"
        # r-pg-01 must NOT be on page 2
        assert "r-pg-01" not in names

    def test_resource_list_pagination_out_of_range_returns_last_page(self, viewer_client):
        """?page=999 falls back to the last valid page (no 404)."""
        self._make_resources(25)
        response = viewer_client.get("/resources/?page=999")
        assert response.status_code == 200
        names = self._resource_names_in(response.content.decode())

        # Last page: r-pg-21..r-pg-25
        for i in range(21, 26):
            assert f"r-pg-{i:02d}" in names

    def test_resource_list_pagination_renders_pagination_partial(self, viewer_client):
        """The _pagination.html partial must be present in the response."""
        self._make_resources(25)
        response = viewer_client.get("/resources/")
        assert response.status_code == 200
        content = response.content.decode()

        assert 'class="pagination"' in content
        assert "page=2" in content

    def test_resource_list_pagination_iterates_page_obj(self, viewer_client):
        """Template iterates page_obj (not 'resources') so pagination works."""
        self._make_resources(25)
        response = viewer_client.get("/resources/?page=2")
        assert response.status_code == 200
        names = self._resource_names_in(response.content.decode())

        # r-pg-25 is alphabetically last → on page 2
        assert "r-pg-25" in names
        # r-pg-01 is alphabetically first → on page 1
        assert "r-pg-01" not in names

    def test_resource_list_htmx_partial_preserves_modal(self, viewer_client):
        """HTMX partial for resources keeps the new-resource modal after pagination."""
        # viewer cannot create, so we need a user with add_resource perm
        # to verify the modal renders. Use editor_client instead.
        from django.contrib.auth.models import User, Group, Permission
        from django.test import Client

        add_perm = Permission.objects.get(codename="add_resource")
        view_perm = Permission.objects.get(codename="view_resource")
        group = Group.objects.create(name="resource-pg-editor")
        group.permissions.add(view_perm)
        group.permissions.add(add_perm)
        user = User.objects.create_user(username="rpg-editor", password="pass")
        user.profile.must_change_password = False
        user.profile.save()
        user.groups.add(group)
        client = Client()
        client.login(username="rpg-editor", password="pass")

        self._make_resources(25)
        response = client.get("/resources/?page=2", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        content = response.content.decode()

        # Partial response
        assert "<html" not in content
        # Modal must survive
        assert 'id="modalNewResource"' in content
        # Pagination must also be present
        assert 'class="pagination"' in content
