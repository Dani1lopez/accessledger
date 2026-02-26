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
    now = timezone.now()