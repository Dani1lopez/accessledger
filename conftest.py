import pytest
from django.contrib.auth.models import User, Group, Permission


@pytest.fixture 
def viewer_client(client):
    group = Group.objects.create(name="viewer")
    permission = Permission.objects.get(codename="view_resource")
    group.permissions.add(permission)
    
    user = User.objects.create_user(username="viewer1", password="pass")
    user.profile.must_change_password = False
    user.profile.save()
    user.groups.add(group)
    
    client.login(username="viewer1", password="pass")
    return client


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
    group = Group.objects.create(name="editor")
    for codename in ["view_resource", "add_resource", "change_resource"]:
        permission = Permission.objects.get(codename=codename)
        group.permissions.add(permission)
    
    user = User.objects.create_user(username="editor1", password="pass")
    user.profile.must_change_password = False
    user.profile.save()
    user.groups.add(group)
    
    client.login(username="editor1", password="pass")
    return client

@pytest.fixture 
def admin_client(client):
    group = Group.objects.create(name="admin")
    for codename in ["view_resource", "add_resource", "change_resource", "delete_resource", "can_grant_access", "can_revoke_access"]:
        permission = Permission.objects.get(codename=codename)
        group.permissions.add(permission)
    
    user = User.objects.create_user(username="admin1", password="pass")
    user.profile.must_change_password = False
    user.profile.save()
    user.groups.add(group)
    
    client.login(username="admin1", password="pass")
    return client

