from axes import admin
import pytest
from django.contrib.auth.models import User, Group, Permission
from core.models import Resource, AccessGrant
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
        response = viewer_client.post("/resources/create/", data={
            "name": "test",
            "resource_type": "server",
            "environment": "dev"
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert response.status_code == 403
    
    def test_editor_can_create(self, editor_client):
        response = editor_client.post(
            "/resources/create/",
            data={
                "name": "nuevo-servidor",
                "resource_type": "server",
                "environment": "dev",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
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
            f"/resources/{resource.pk}/delete/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        assert response.status_code == 403
    
    def test_admin_can_delete(self, admin_client):
        resource = Resource.objects.create(
            name="test-user",
            resource_type="server",
        )
        response = admin_client.post(
            f"/resources/{resource.pk}/delete/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
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
        response = admin_client.post("/users/create/", data={
            "username": "newuser",
            "email": "new@test.com",
            "first_name": "New",
            "last_name": "User",
            "password": "testpass123",
            "role": group.pk,
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

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
