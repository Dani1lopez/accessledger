"""Tests for ``_ensure_must_change_profile``.

REQ-AR-012 Scenario 12.7 — the defensive form MUST be preserved.
``test_views.py::test_password_update_creates_profile_if_missing``
deletes the target Profile and expects the view to recreate it.
"""
import pytest

from core.utils.profile import _ensure_must_change_profile
from core.models import Profile


@pytest.mark.django_db
class TestEnsureMustChangeProfile:
    def test_creates_profile_if_missing(self):
        """REQ-AR-012 Scenario 12.7 — defensive: missing Profile gets created."""
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="newprofile", password="x")
        # Delete the auto-created profile to simulate missing row
        Profile.objects.filter(user=user).delete()
        assert not Profile.objects.filter(user=user).exists()

        profile = _ensure_must_change_profile(user)

        assert Profile.objects.filter(user=user).exists()
        assert profile.must_change_password is True

    def test_is_idempotent(self):
        """Calling twice does not duplicate the profile or change semantics."""
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="idem", password="x")
        p1 = _ensure_must_change_profile(user)
        p2 = _ensure_must_change_profile(user)
        assert p1.pk == p2.pk
        assert Profile.objects.filter(user=user).count() == 1
        assert p2.must_change_password is True

    def test_overrides_existing_false(self):
        """The helper always sets must_change_password=True, overriding any prior state."""
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="override", password="x")
        user.profile.must_change_password = False
        user.profile.save()

        profile = _ensure_must_change_profile(user)

        profile.refresh_from_db()
        assert profile.must_change_password is True