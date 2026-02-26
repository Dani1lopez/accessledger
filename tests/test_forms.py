import pytest
from django.utils import timezone
from datetime import timedelta
from core.forms import AccessGrantForm
from django.contrib.auth.models import User
from core.models import Resource

@pytest.fixture
def user(db):
    return User.objects.create_user(username="tester", password="pass1234!")

@pytest.fixture
def resource(db, user):
    return Resource.objects.create(
        name="test-resource",
        resource_type=Resource.ResourceType.SERVER,
        owner=user,
    )

def grant_payload(user, resource, start_offset_hours=0, end_offset_hours=24):
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    return {
        "user": user.pk,
        "access_level": "read",
        "start_at": (now + timedelta(hours=start_offset_hours)).strftime("%Y-%m-%d %H:%M:%S"),
        "end_at": (now + timedelta(hours=end_offset_hours)).strftime("%Y-%m-%d %H:%M:%S"),
        "notes": "",
    }

class TestAccessGrantFormClean:
    
    def test_valid_dates(self, user, resource):
        form = AccessGrantForm(data=grant_payload(user, resource))
        assert form.is_valid(), form.errors
    
    def test_same_day_different_hours_valid(self, user, resource):
        form = AccessGrantForm(data=grant_payload(user, resource, start_offset_hours=0, end_offset_hours=8))
        assert form.is_valid(), form.errors
    
    def test_exact_same_datetime_hours_invalid(self, user, resource):
        form = AccessGrantForm(data=grant_payload(user, resource, start_offset_hours=8, end_offset_hours=8))
        assert not form.is_valid()
        assert "__all__" in form.errors
    
    def test_end_at_before_start_at_invalid(self, user, resource):
        form = AccessGrantForm(data=grant_payload(user, resource, start_offset_hours=9, end_offset_hours=6))
        assert not form.is_valid()
        assert "__all__" in form.errors
    
    def test_missing_end_at_no_crash(self, user, resource):
        payload = grant_payload(user, resource)
        payload.pop("end_at")
        form = AccessGrantForm(data=payload)
        assert not form.is_valid()
        assert "end_at" in form.errors
        assert "__all__" not in form.errors