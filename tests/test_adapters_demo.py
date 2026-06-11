"""Tests for the demo (no-op) adapter. Per spec: DemoAdapter.sync()
returns ok with the DEMO / no-op detail; no DB or network I/O."""
import inspect

from core.adapters.base import SyncResult
from core.adapters.demo import DemoAdapter


class TestDemoAdapter:
    def test_returns_ok_true_with_no_op_detail(self):
        result = DemoAdapter().sync()
        assert isinstance(result, SyncResult)
        assert result.ok is True
        assert "no-op" in result.detail
        assert "DEMO" in result.detail

    def test_is_idempotent(self):
        a = DemoAdapter().sync()
        b = DemoAdapter().sync()
        assert a.ok == b.ok
        assert a.detail == b.detail

    def test_demo_module_does_not_import_models(self):
        from core.adapters import demo as demo_module
        for name in dir(demo_module):
            mod = getattr(getattr(demo_module, name), "__module__", "")
            assert not mod.startswith("core.models"), f"Demo module leaked ORM import: {name} from {mod}"

    def test_sync_method_body_has_no_io_tokens(self):
        source = inspect.getsource(DemoAdapter.sync)
        forbidden = ("open(", "requests.", "httpx.", "aiohttp", "urllib", "socket", "Resource.", "AccessGrant.", ".save(")
        for token in forbidden:
            assert token not in source, f"DemoAdapter.sync body should not contain '{token}': {source}"
