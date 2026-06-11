"""Tests for the `demo_sync` management command."""
import io
import importlib

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

import core.adapters.demo  # noqa: F401  — triggers @register on import


@pytest.fixture(autouse=True)
def _ensure_demo_registered():
    importlib.reload(core.adapters.demo)
    yield


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
