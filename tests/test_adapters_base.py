"""Tests for the adapter base contract."""
import pytest
from dataclasses import FrozenInstanceError, fields

from core.adapters.base import ResourceAdapter, SyncResult


class TestAdapterBaseContract:
    def test_syncresult_has_ok_and_detail_fields(self):
        assert {f.name for f in fields(SyncResult)} == {"ok", "detail"}

    def test_syncresult_default_detail_is_empty_string(self):
        assert SyncResult(ok=True).detail == ""

    def test_syncresult_is_frozen_assignment_raises(self):
        sr = SyncResult(ok=True, detail="x")
        with pytest.raises(FrozenInstanceError):
            sr.ok = False  # type: ignore[misc]

    def test_cannot_instantiate_resourceadapter_directly(self):
        with pytest.raises(TypeError):
            ResourceAdapter()  # type: ignore[abstract]

    def test_subclass_without_sync_is_still_abstract(self):
        class _Incomplete(ResourceAdapter):
            pass
        with pytest.raises(TypeError):
            _Incomplete()  # type: ignore[abstract]
