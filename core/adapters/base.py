"""Adapter base contract: ABC + frozen SyncResult."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SyncResult:
    """Outcome of an adapter sync(). ok + optional human-readable detail."""
    ok: bool
    detail: str = ""


class ResourceAdapter(ABC):
    """Abstract base for V2 external service adapters."""

    @abstractmethod
    def sync(self) -> SyncResult:
        """Run the adapter's synchronization and return its outcome."""
        ...
