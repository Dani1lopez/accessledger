import pytest
from django.contrib.auth.models import User
from core.models import AccessGrant, Resource, Profile
from datetime import timedelta
from django.utils import timezone

@pytest.mark.django_db
class TestResourceModel:
    def test_str(self):
        resource = Resource.objects.create(
            name="test-server",
            resource_type=Resource.ResourceType.SERVER,
        )
        assert str(resource) == "test-server"

@pytest.mark.django_db
class TestAccessGrantModel:
    def test_str(self):
        user = User.objects.create_user(username="testuser", password="pass")
        resource = Resource.objects.create(
            name="test-server",
            resource_type=Resource.ResourceType.SERVER,
        )
        grant = AccessGrant.objects.create(
            user=user,
            resource=resource,
            access_level=AccessGrant.AccessLevel.READ,
            start_at=timezone.now(),
            end_at=timezone.now() + timedelta(days=30)
        )
        
        assert str(grant) == "testuser → test-server (read)"

@pytest.mark.django_db
class TestProfileSignal:
    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(username="testuser", password="pass")
        assert Profile.objects.filter(user=user).exists()
    
    def test_must_change_password_default_true(self):
        user = User.objects.create_user(username="testuser", password="pass")
        profile = Profile.objects.get(user=user)
        assert profile.must_change_password is True