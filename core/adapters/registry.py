"""Adapter registry: in-memory whitelist of admissible adapter targets.

Only @register-decorated ResourceAdapter subclasses are resolvable.
Unregistered targets are rejected even when importable.
"""
from __future__ import annotations

from .base import ResourceAdapter


class AdapterRegistrationError(ValueError):
    """Raised when a class cannot be registered as an adapter."""


class AdapterLookupError(KeyError):
    """Raised when the registry cannot resolve a requested adapter path."""

    def __init__(self, dotted_path: str) -> None:
        super().__init__(dotted_path)
        self.dotted_path = dotted_path

    def __str__(self) -> str:
        return f"Adapter '{self.dotted_path}' is not registered. Only classes explicitly @register-decorated can be resolved."


# dotted path -> adapter class
_registry: dict[str, type[ResourceAdapter]] = {}


def register(cls: type[ResourceAdapter]) -> type[ResourceAdapter]:
    """Class decorator: validate and store ``cls`` by its dotted path."""
    if not isinstance(cls, type):
        raise AdapterRegistrationError(f"@register target must be a class, got {type(cls).__name__}")
    if not issubclass(cls, ResourceAdapter):
        raise AdapterRegistrationError(f"{cls!r} must subclass ResourceAdapter to be registered")
    abstract = getattr(cls, "__abstractmethods__", frozenset())
    if abstract:
        raise AdapterRegistrationError(f"{cls!r} has unimplemented abstract methods: {sorted(abstract)}")
    _registry[f"{cls.__module__}.{cls.__qualname__}"] = cls
    return cls


def get_adapter(dotted_path: str) -> ResourceAdapter:
    """Resolve a registered adapter path to a fresh instance. Never imports."""
    if not dotted_path:
        raise AdapterLookupError("")
    try:
        cls = _registry[dotted_path]
    except KeyError as exc:
        raise AdapterLookupError(dotted_path) from exc
    return cls()


__all__ = ["AdapterRegistrationError", "AdapterLookupError", "register", "get_adapter"]
