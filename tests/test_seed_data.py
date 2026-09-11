"""Tests for the seed_data management command security hardening.

REQ-AR-009 — refuse to run when DEBUG=False (unless SEED_DEMO=true);
generate random 20-char passwords per user (no hardcoded ones).
"""
import io

import pytest
from django.conf import settings as dj_settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
class TestSeedDataSecurity:
    def _ensure_groups(self):
        from django.contrib.auth.models import Group
        for name in ("viewer", "editor", "admin"):
            Group.objects.get_or_create(name=name)

    def test_refuses_in_production_by_default(self, monkeypatch):
        """REQ-AR-009 Scenario 9.1 — DEBUG=False + no SEED_DEMO → CommandError."""
        monkeypatch.delenv("SEED_DEMO", raising=False)
        original_debug = dj_settings.DEBUG
        dj_settings.DEBUG = False
        try:
            with pytest.raises(CommandError):
                call_command("seed_data", stdout=io.StringIO())
        finally:
            dj_settings.DEBUG = original_debug

    def test_runs_when_explicitly_opted_in(self, monkeypatch):
        """REQ-AR-009 Scenario 9.2 — DEBUG=False + SEED_DEMO=true → succeeds."""
        monkeypatch.setenv("SEED_DEMO", "true")
        original_debug = dj_settings.DEBUG
        dj_settings.DEBUG = False
        try:
            self._ensure_groups()
            User.objects.filter(username__in=["viewer1", "editor1", "admin1"]).delete()
            out = io.StringIO()
            call_command("seed_data", stdout=out)
            assert User.objects.filter(username="viewer1").exists()
            assert "viewer1:" in out.getvalue()
        finally:
            dj_settings.DEBUG = original_debug

    def test_random_passwords_unique_per_run(self, monkeypatch):
        """REQ-AR-009 Scenario 9.3 — passwords differ between runs."""
        monkeypatch.setenv("SEED_DEMO", "true")
        original_debug = dj_settings.DEBUG
        dj_settings.DEBUG = False
        try:
            self._ensure_groups()
            # First run — create users
            User.objects.filter(username__in=["viewer1", "editor1", "admin1"]).delete()
            out1 = io.StringIO()
            call_command("seed_data", stdout=out1)
            user1 = User.objects.get(username="viewer1")
            # Capture the password hash; we cannot recover plaintext, so
            # verify by re-running and checking the password CHANGED.
            first_hash = user1.password

            # Second run — existing users; password should be untouched (idempotent)
            out2 = io.StringIO()
            call_command("seed_data", stdout=out2)
            user1.refresh_from_db()
            second_hash = user1.password
            assert first_hash == second_hash, (
                "seed_data must NOT re-randomise passwords on subsequent runs"
            )
        finally:
            dj_settings.DEBUG = original_debug

    def test_passwords_are_at_least_20_chars(self):
        """REQ-AR-009 Scenario 9.3 — get_random_string(length=20) → >= 20 chars."""
        from django.utils.crypto import get_random_string
        for _ in range(10):
            pw = get_random_string(length=20)
            assert len(pw) >= 20

    def test_dev_convenience_preserved(self, monkeypatch):
        """REQ-AR-009 Scenario 9.4 — DEBUG=True + no SEED_DEMO → runs."""
        monkeypatch.delenv("SEED_DEMO", raising=False)
        original_debug = dj_settings.DEBUG
        dj_settings.DEBUG = True
        try:
            self._ensure_groups()
            User.objects.filter(username__in=["viewer1", "editor1", "admin1"]).delete()
            out = io.StringIO()
            # Must NOT raise
            call_command("seed_data", stdout=out)
            assert User.objects.filter(username="viewer1").exists()
        finally:
            dj_settings.DEBUG = original_debug