"""Tests for the adapter registry. Per spec: @register accepts
ResourceAdapter subclasses and rejects non-adapters; get_adapter rejects
unregistered paths WITHOUT importing anything."""
import importlib

import pytest

from core.adapters.base import ResourceAdapter, SyncResult
from core.adapters import registry


@pytest.fixture(autouse=True)
def _clean_registry():
    registry._registry.clear()
    yield
    registry._registry.clear()


class _StubAdapter(ResourceAdapter):
    def sync(self):
        return SyncResult(ok=True, detail="stub")


class TestRegisterDecoratorAcceptsValidAdapter:
    def test_register_makes_adapter_resolvable(self):
        registry.register(_StubAdapter)
        path = f"{_StubAdapter.__module__}.{_StubAdapter.__qualname__}"
        instance = registry.get_adapter(path)
        assert isinstance(instance, _StubAdapter)


class TestRegisterDecoratorRejectsNonAdapters:
    def test_rejects_plain_class_without_resourceadapter_base(self):
        class _NotAnAdapter:
            def sync(self):
                return SyncResult(ok=True)
        with pytest.raises(registry.AdapterRegistrationError):
            registry.register(_NotAnAdapter)

    def test_rejects_function_target(self):
        def _not_a_class():
            return SyncResult(ok=True)
        with pytest.raises(registry.AdapterRegistrationError):
            registry.register(_not_a_class)


class TestGetAdapterRejection:
    def test_unknown_path_raises(self):
        with pytest.raises(registry.AdapterLookupError):
            registry.get_adapter("does.not.exist.X")

    def test_empty_path_raises(self):
        with pytest.raises(registry.AdapterLookupError):
            registry.get_adapter("")

    def test_importable_but_unregistered_class_is_rejected(self):
        """The autouse fixture cleared the registry, so even an importable
        class at the path must be rejected."""
        path = f"{_StubAdapter.__module__}.{_StubAdapter.__qualname__}"
        assert importlib.import_module(_StubAdapter.__module__).__dict__.get(_StubAdapter.__qualname__) is _StubAdapter
        with pytest.raises(registry.AdapterLookupError):
            registry.get_adapter(path)
