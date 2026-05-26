import pytest
from django.contrib.auth.models import User
from core.models import AccessGrant, Resource, Profile, AuditLog
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
class TestAuditLogIndex:
    def test_timestamp_field_has_db_index(self):
        """AuditLog.timestamp must have db_index=True for efficient ordering."""
        field = AuditLog._meta.get_field('timestamp')
        assert field.db_index is True, (
            f"AuditLog.timestamp db_index is {field.db_index}, expected True"
        )

    def test_timestamp_ordering_preserved(self):
        """Descending timestamp ordering still works with the index."""
        user = User.objects.create_user(username="audituser", password="pass")
        AuditLog.objects.create(
            user=user,
            action=AuditLog.Action.RESOURCE_CREATED,
            object_type="resource",
            object_id=1,
            object_repr="test",
        )
        results = list(AuditLog.objects.all().order_by("-timestamp"))
        assert len(results) == 1
        assert results[0].action == AuditLog.Action.RESOURCE_CREATED

@pytest.mark.django_db
class TestProfileSignal:
    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(username="testuser", password="pass")
        assert Profile.objects.filter(user=user).exists()

    def test_must_change_password_default_true(self):
        user = User.objects.create_user(username="testuser", password="pass")
        profile = Profile.objects.get(user=user)
        assert profile.must_change_password is True