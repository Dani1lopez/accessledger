"""Snapshot helpers used by audit-log emission.

Pure functions over already-loaded model instances. No DB queries.
A new field in ``Resource`` / ``AccessGrant`` only requires updating
one helper, not 5+ call sites.

These helpers are the single source of truth for the data written
into ``AuditLog.before`` / ``AuditLog.after`` JSONField columns.
"""
from __future__ import annotations


def resource_snapshot(resource) -> dict:
    """Return a JSON-safe dict for the given ``Resource`` instance.

    Schema (fixed order — tests assert key equality):

        name, resource_type, environment, url, is_active, owner

    ``owner`` is the owner's username, or ``None`` if the resource
    has no owner. Including ``owner`` closes the audit-flagged drift
    at ``core/views.py:159-165``.
    """
    return {
        "name": resource.name,
        "resource_type": resource.resource_type,
        "environment": resource.environment,
        "url": resource.url,
        "is_active": resource.is_active,
        "owner": resource.owner.username if resource.owner else None,
    }


def grant_snapshot(grant) -> dict:
    """Return a JSON-safe dict for the given ``AccessGrant`` instance.

    Schema (fixed order — tests assert key equality):

        user, resource, access_level, status, start_at, end_at, notes

    Dates are ISO-formatted. ``end_at`` is ``None`` when missing.
    """
    return {
        "user": grant.user.username,
        "resource": grant.resource.name,
        "access_level": grant.access_level,
        "status": grant.status,
        "start_at": grant.start_at.isoformat(),
        "end_at": grant.end_at.isoformat() if grant.end_at else None,
        "notes": grant.notes,
    }


def user_role(user) -> str | None:
    """Return the name of the user's first group, or ``None``.

    Defensive: returns ``None`` instead of raising ``AttributeError``
    when ``user.groups`` is empty (audit-flagged regression at
    ``core/views.py:391``). User objects expose ``groups`` only when
    the auth user model supports groups; ``str | None`` keeps the
    call site free of ``None`` handling logic.
    """
    if user.groups.exists():
        return user.groups.first().name
    return None