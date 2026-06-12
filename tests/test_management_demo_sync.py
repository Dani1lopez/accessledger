"""Tests for the `demo_sync` management command."""
import io
import importlib

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

import core.adapters.demo  # noqa: F401  — triggers @register on import
from core.adapters.base import ResourceAdapter, SyncResult
from core.adapters import registry


@pytest.fixture(autouse=True)
def _ensure_demo_registered():
    importlib.reload(core.adapters.demo)
    yield


class _FailingAdapter(ResourceAdapter):
    """Stub adapter whose sync() reports ok=False. Registered locally inside
    the boundary test (NOT at module import time) so that other test files'
    registry-clearing teardowns do not strip the path before our test runs.
    The class-level ``sync_calls`` counter lets the test prove the
    ``CommandError`` originated from the ``ok=False`` boundary, not from
    registry lookup failure (G2)."""

    sync_calls = 0

    def sync(self) -> SyncResult:
        _FailingAdapter.sync_calls += 1
        return SyncResult(ok=False, detail="synthetic failure")


_FailingAdapter.__module__ = "tests.test_management_demo_sync"
_FailingAdapter.__qualname__ = "_FailingAdapter"
FAILING_ADAPTER_PATH = f"{_FailingAdapter.__module__}.{_FailingAdapter.__qualname__}"


class TestDemoSyncCommand:
    def test_default_run_succeeds_and_prints_banner(self):
        out = io.StringIO()
        call_command("demo_sync", stdout=out)
        output = out.getvalue()
        assert "DEMO" in output
        assert "no-op" in output

    def test_explicit_demo_path_succeeds(self):
        out = io.StringIO()
        call_command("demo_sync", "--adapter", "core.adapters.demo.DemoAdapter", stdout=out)
        assert "DEMO" in out.getvalue()

    def test_unknown_dotted_path_raises_command_error(self):
        with pytest.raises(CommandError):
            call_command("demo_sync", "--adapter", "does.not.exist.X", stdout=io.StringIO())

    def test_unregistered_but_importable_path_raises_command_error(self):
        """A path that resolves via importlib but was never @registered
        must be rejected — the registry must not silently import."""
        fake_path = f"{__name__}._definitely_not_registered"
        with pytest.raises(CommandError):
            call_command("demo_sync", "--adapter", fake_path, stdout=io.StringIO())

    def test_adapter_failure_raises_command_error_at_boundary(self):
        """When the resolved adapter returns SyncResult(ok=False, ...), the
        command boundary must surface that as CommandError so operators
        see a clear failure (G2 — boundary-only contract).

        The adapter is registered locally inside this test (not at module
        import time) so prior test files clearing ``registry._registry``
        in their teardowns cannot leave the path unregistered. The
        ``sync_calls`` counter then forces the failure to have originated
        in the ``ok=False`` branch: if the ``CommandError`` had come from
        registry lookup (line 28 of demo_sync.py), the counter would
        still be 0 and this assertion would fail — which is exactly the
        false-positive the verification report flagged."""
        _FailingAdapter.sync_calls = 0
        registry.register(_FailingAdapter)
        try:
            with pytest.raises(CommandError):
                call_command("demo_sync", "--adapter", FAILING_ADAPTER_PATH, stdout=io.StringIO())
            assert _FailingAdapter.sync_calls == 1, (
                f"Expected exactly one sync() call before boundary raise; "
                f"got {_FailingAdapter.sync_calls}. If 0, the CommandError "
                f"came from registry lookup, not from the ok=False boundary."
            )
        finally:
            registry._registry.pop(FAILING_ADAPTER_PATH, None)
