import os
import pytest
from django.contrib.auth.models import User, Group, Permission

os.environ["POSTGRES_HOST"] = "127.0.0.1"
os.environ["POSTGRES_PORT"] = "5432"


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

