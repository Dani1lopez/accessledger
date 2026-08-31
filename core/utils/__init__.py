"""Utils package — pure helpers, no DB queries at import time.

Re-exports ``log_action`` for backward compatibility. Callers do
``from core.utils import log_action`` or ``from .utils import log_action``.
"""
from .log_action import log_action

__all__ = ["log_action"]