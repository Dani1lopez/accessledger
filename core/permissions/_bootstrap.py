"""Shared admin-group permission seeding.

Single source of truth for the admin group's permission set, shared
by ``bootstrap_roles`` and ``ensure_superuser``. Adding/removing a
codename in ``ADMIN_GROUP_PERMISSIONS`` updates both commands.

The function imports Group / Permission / ContentType from
auth/contenttypes, so co-location with ``core/permissions/`` matches
the package's purpose. Underscore prefix signals 'internal bootstrap
helper', matching Django convention for semi-private modules.
"""
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from core.models import Resource
from core.permissions.constants import ADMIN_GROUP_PERMISSIONS


def seed_admin_permissions(group: Group, *, stdout=None) -> None:
    """Seed ``group`` with every codename in ``ADMIN_GROUP_PERMISSIONS``.

    Looks up each codename via the ``Resource`` ContentType first (most
    RBAC codenames are Resource-scoped), then falls back to a global
    codename lookup for custom permissions that have no ContentType
    binding (``can_grant_access`` / ``can_revoke_access``).

    Unknown codenames are skipped silently — a future migration may
    add codenames before the ContentType is registered, and the
    seeding must remain forward-compatible.

    If ``stdout`` is provided, writes a single checkmark line per
    added permission (matches the existing ``bootstrap_roles`` UX).
    """
    if not isinstance(group, Group):
        raise TypeError(
            f"seed_admin_permissions expected Group, got {type(group).__name__}"
        )

    ct = ContentType.objects.get_for_model(Resource)
    for codename in ADMIN_GROUP_PERMISSIONS:
        try:
            perm = Permission.objects.get(content_type=ct, codename=codename)
        except Permission.DoesNotExist:
            # Custom permission (no ContentType binding) — look up by codename only.
            try:
                perm = Permission.objects.get(codename=codename)
            except Permission.DoesNotExist:
                # Codename not registered yet — skip without failing.
                continue
        if not group.permissions.filter(pk=perm.pk).exists():
            group.permissions.add(perm)
            if stdout is not None:
                stdout.write(f"OK Asignado {codename} a {group.name}")