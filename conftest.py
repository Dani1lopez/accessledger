import pytest
from django.contrib.auth.models import User, Group, Permission


def _make_role_client(client, role_name, codenames, username):
    """Create a logged-in client with the named role and given codenames.

    Centralised factory for the role-fixture trio. Each public fixture
    (viewer_client, editor_client, admin_client) is a thin wrapper
    around this so test parametrization stays stable.

    Returns the logged-in ``client`` (the same object passed in).
    """
    group = Group.objects.create(name=role_name)
    for codename in codenames:
        permission = Permission.objects.get(codename=codename)
        group.permissions.add(permission)

    user = User.objects.create_user(username=username, password="pass")
    user.profile.must_change_password = False
    user.profile.save()
    user.groups.add(group)

    client.login(username=username, password="pass")
    return client


@pytest.fixture
def viewer_client(client):
    """REQ-AR-006 Scenario 6.1 — viewer_client, thin wrapper around _make_role_client."""
    return _make_role_client(
        client,
        role_name="viewer",
        codenames=["view_resource"],
        username="viewer1",
    )


@pytest.fixture
def forced_password_client(client):
    """Authenticated user with must_change_password=True (forced redirect)."""
    user = User.objects.create_user(username="forced1", password="ForcedPass123!")
    # Profile auto-created via post_save with must_change_password=True (default)
    assert user.profile.must_change_password is True
    client.login(username="forced1", password="ForcedPass123!")
    return client


@pytest.fixture
def editor_client(client):
    """REQ-AR-006 Scenario 6.1 — editor_client, thin wrapper around _make_role_client."""
    return _make_role_client(
        client,
        role_name="editor",
        codenames=["view_resource", "add_resource", "change_resource"],
        username="editor1",
    )


@pytest.fixture
def admin_client(client):
    """REQ-AR-006 Scenario 6.1 — admin_client, thin wrapper around _make_role_client.

    The 6-codename tuple MUST match ``ADMIN_GROUP_PERMISSIONS`` in
    ``core.permissions.constants`` (regression lock, asserted by the
    new test_permissions_bootstrap suite).
    """
    return _make_role_client(
        client,
        role_name="admin",
        codenames=[
            "view_resource",
            "add_resource",
            "change_resource",
            "delete_resource",
            "can_grant_access",
            "can_revoke_access",
        ],
        username="admin1",
    )


@pytest.mark.django_db
class TestMakeRoleClient:
    """REQ-AR-006 Scenario 6.2 — factory centralizes role bootstrap."""

    def test_factory_creates_logged_in_client_with_role(self, client):
        from conftest import _make_role_client
        client = _make_role_client(
            client,
            role_name="custom-role",
            codenames=["view_resource"],
            username="custom1",
        )
        # Client must be authenticated.
        response = client.get("/resources/")
        assert response.status_code == 200
        # Group must carry the specified codenames.
        from django.contrib.auth.models import Group
        group = Group.objects.get(name="custom-role")
        assert set(group.permissions.values_list("codename", flat=True)) == {
            "view_resource"
        }

