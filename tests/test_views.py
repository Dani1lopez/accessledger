from axes import admin
import pytest
from django.contrib.auth.models import User, Group, Permission
from core.models import Resource, AccessGrant, AuditLog
from django.utils import timezone
from datetime import timedelta


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
    """Verify auth pages render without the full navigation topbar."""

    def test_password_change_page_has_no_topbar(self, forced_password_client):
        """Password change page must NOT include the topbar header when forced."""
        response = forced_password_client.get("/password/change/")
        assert response.status_code == 200
        content = response.content.decode()
        assert '<header class="topbar"' not in content

    def test_password_change_page_has_no_logout_form(self, forced_password_client):
        """Password change page must NOT include a logout form."""
        response = forced_password_client.get("/password/change/")
        assert response.status_code == 200
        content = response.content.decode()
        assert 'action="/logout/"' not in content

    def test_login_page_has_no_topbar(self, client):
        """Login page must NOT include the full nav topbar."""
        response = client.get("/login/")
        assert response.status_code == 200
        content = response.content.decode()
        assert '<header class="topbar"' not in content

    def test_lockout_page_has_no_topbar(self):
        """Lockout template must NOT include the full nav topbar (rendered by axes during lockout)."""
        from django.template.loader import render_to_string
        html = render_to_string("axes/lockout.html")
        assert '<header class="topbar"' not in html

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
