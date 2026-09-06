"""Profile helpers used by ``user_update`` when an admin sets a password.

This module is the SINGLE home for the defensive
``Profile.objects.get_or_create(...)`` block. The block is defensive
by design — ``tests/test_views.py::test_password_update_creates_profile_if_missing``
deletes the target user's ``Profile`` and expects the view to recreate
it. The audit's 'redundant' claim was incorrect; the defensive form
guards against a missing Profile row when an admin rotates a
password for a user that, for any reason, lacks one.
"""
from core.models import Profile


def _ensure_must_change_profile(user) -> Profile:
    """Return the user's ``Profile`` and ensure ``must_change_password=True``.

    Idempotent. Creates the Profile if missing (defensive) and always
    sets ``must_change_password=True`` so the admin-set password forces
    the target user through ``ForcePasswordChangeMiddleware`` on next login.
    """
    profile, _created = Profile.objects.get_or_create(
        user=user, defaults={"must_change_password": True}
    )
    profile.must_change_password = True
    profile.save()
    return profile