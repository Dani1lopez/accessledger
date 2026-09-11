"""Tests for ensure_superuser's --require-env flag and DEBUG-aware fail-closed.

REQ-AR-007 Scenarios 7.8, 7.9, 7.10 — the command must fail closed when
DEBUG=False or --require-env is set, and must preserve the dev warning +
exit 0 convenience flow when DEBUG=True.
"""
import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


class TestRequireEnv:
    """Tests for the --require-env flag and DEBUG-aware fail-closed."""

    pytestmark = pytest.mark.django_db

    def test_debug_true_preserves_dev_warning(self, monkeypatch):
        """REQ-AR-007 Scenario 7.9 — DEBUG=True + no env → WARNING + exit 0."""
        monkeypatch.delenv("DJANGO_SUPERUSER_USERNAME", raising=False)
        monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)
        from django.conf import settings as dj_settings
        original_debug = dj_settings.DEBUG
        dj_settings.DEBUG = True
        try:
            out = io.StringIO()
            call_command("ensure_superuser", stdout=out)
            assert "SKIP" in out.getvalue()
        finally:
            dj_settings.DEBUG = original_debug

    def test_debug_false_fails_closed(self, monkeypatch):
        """REQ-AR-007 Scenario 7.8 — DEBUG=False + no env → CommandError."""
        monkeypatch.delenv("DJANGO_SUPERUSER_USERNAME", raising=False)
        monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)
        from django.conf import settings as dj_settings
        original_debug = dj_settings.DEBUG
        dj_settings.DEBUG = False
        try:
            with pytest.raises(CommandError):
                call_command("ensure_superuser", stdout=io.StringIO())
        finally:
            dj_settings.DEBUG = original_debug

    def test_require_env_flag_forces_fail_closed_in_dev(self, monkeypatch):
        """REQ-AR-007 Scenario 7.10 — DEBUG=True + --require-env + no env → CommandError."""
        monkeypatch.delenv("DJANGO_SUPERUSER_USERNAME", raising=False)
        monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)
        from django.conf import settings as dj_settings
        original_debug = dj_settings.DEBUG
        dj_settings.DEBUG = True
        try:
            with pytest.raises(CommandError):
                call_command("ensure_superuser", "--require-env", stdout=io.StringIO())
        finally:
            dj_settings.DEBUG = original_debug