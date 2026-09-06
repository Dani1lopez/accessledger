"""Tests for ``seed_admin_permissions``.

REQ-AR-006 Scenario 6.3 — the shared helper must produce the same
final permission set when called from bootstrap_roles and ensure_superuser.
"""
import io

import pytest

from core.permissions._bootstrap import seed_admin_permissions
from core.permissions.constants import ADMIN_GROUP_PERMISSIONS


@pytest.mark.django_db
class TestSeedAdminPermissions:
    def test_seeds_all_admin_codenames(self):
        from django.contrib.auth.models import Group, Permission
        group = Group.objects.create(name="admin")
        seed_admin_permissions(group)

        assigned = set(
            group.permissions.values_list("codename", flat=True)
        )
        registered = set(
            Permission.objects.values_list("codename", flat=True)
        )
        # Every constant codename registered in the DB must end up on the group.
        assert assigned == set(ADMIN_GROUP_PERMISSIONS) & registered

    def test_is_idempotent(self):
        from django.contrib.auth.models import Group
        group = Group.objects.create(name="admin")
        seed_admin_permissions(group)
        first_count = group.permissions.count()

        seed_admin_permissions(group)
        second_count = group.permissions.count()
        assert first_count == second_count

    def test_writes_stdout_for_new_perms(self):
        from django.contrib.auth.models import Group
        group = Group.objects.create(name="admin")
        out = io.StringIO()
        seed_admin_permissions(group, stdout=out)
        assert out.getvalue().count("Asignado") >= 1

    def test_same_set_via_two_calls(self):
        """REQ-AR-006 Scenario 6.3 — both call sites must produce the
        same final permission set. Verified by calling the helper twice
        (simulating bootstrap_roles + ensure_superuser) on different
        Group instances and comparing the resulting permission sets."""
        from django.contrib.auth.models import Group
        g1 = Group.objects.create(name="admin-1")
        g2 = Group.objects.create(name="admin-2")

        seed_admin_permissions(g1)
        seed_admin_permissions(g2)

        s1 = set(g1.permissions.values_list("codename", flat=True))
        s2 = set(g2.permissions.values_list("codename", flat=True))
        assert s1 == s2

    def test_rejects_non_group_argument(self):
        with pytest.raises(TypeError):
            seed_admin_permissions("not-a-group")