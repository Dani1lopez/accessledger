"""Permissions package.

Re-exports the existing `user_can_modify_resource` helper for backward
compatibility (callers do `from core.permissions import user_can_modify_resource`).
Also hosts the shared admin-group permission set consumed by
`bootstrap_roles` and `ensure_superuser` (see `core.permissions.constants`).
"""
from .helpers import user_can_modify_resource  # noqa: F401

__all__ = ["user_can_modify_resource"]
