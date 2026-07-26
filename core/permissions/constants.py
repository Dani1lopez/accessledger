"""Single source of truth for the admin group's permission set.

Used by both `bootstrap_roles` and `ensure_superuser` so the two commands
stay in sync. Adding/removing a codename here updates both commands.

These codenames match the lock file in `tests/conftest.py::admin_client`
(REGRESSION GUARD) and the spec REQ-003 contract.
"""
ADMIN_GROUP_PERMISSIONS = (
    "view_resource",
    "add_resource",
    "change_resource",
    "delete_resource",
    "can_grant_access",
    "can_revoke_access",
)
