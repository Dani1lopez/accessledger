"""Demo adapter: explicit NO-OP, manual demonstration only.

``DemoAdapter`` returns success without any external I/O, DB writes, or
provider-specific work. The ``DEMO / no-op`` detail string makes the
non-production intent unambiguous.
"""
from __future__ import annotations

from .base import ResourceAdapter, SyncResult
from .registry import register


@register
class DemoAdapter(ResourceAdapter):
    """Explicit no-op adapter. Returns a successful DEMO / no-op result."""

    def sync(self) -> SyncResult:
        return SyncResult(ok=True, detail="DEMO / no-op")
