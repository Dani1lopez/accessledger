"""V2 adapter contract public surface."""
from .base import ResourceAdapter, SyncResult
from .demo import DemoAdapter
from .registry import (AdapterLookupError, AdapterRegistrationError,
                       get_adapter, register)

__all__ = ["ResourceAdapter", "SyncResult", "register", "get_adapter",
           "AdapterRegistrationError", "AdapterLookupError", "DemoAdapter"]
