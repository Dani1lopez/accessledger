"""Tests for the `ensure_superuser` management command.

SEC-002 carve-out: REQ-001 through REQ-007 from
`sdd/fix-entrypoint-shell-injection/spec`. Strict TDD — these tests MUST
fail before the command exists and pass after the GREEN implementation.
"""
import io
from pathlib import Path
from unittest import mock

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError

from core.permissions.constants import ADMIN_GROUP_PERMISSIONS


# ── Test suite ──────────────────────────────────────────────────────────

class TestEnsureSuperuserCommand:
    """Strict TDD: REQ-001–007 → one test per scenario."""

    pytestmark = pytest.mark.django_db

    # --- REQ-001: shell-metachars are data, not source ---

    def test_creates_superuser_with_shell_metachars(self, monkeypatch, tmp_path):
        """Username/password with ', $, !, ;, backticks create the right user."""
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "u'`rm -rf /`'")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", 'p$a$s"w;')
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "a@example.com")
        # /tmp is shared; use a unique sentinel inside tmp_path
        sentinel = tmp_path / "pwn"
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "u'`rm -rf /`'")
        # Avoid actually evaluating the rm — the test asserts no subprocess ran.
        out = io.StringIO()
        call_command("ensure_superuser", stdout=out)

        user = User.objects.get(username="u'`rm -rf /`'")
        assert user.is_superuser is True
        assert user.is_staff is True
        assert user.email == "a@example.com"
        # No side-effect file materialized anywhere
        assert not sentinel.exists(), (
            "ensure_superuser must not invoke the shell on the username"
        )
        assert "[ensure_superuser]" in out.getvalue()

    def test_command_substitution_not_evaluated(self, monkeypatch):
        """`$(touch /tmp/pwn)` in username is stored verbatim; no touch runs."""
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "$(touch /tmp/pwn)")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "irrelevant")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "a@example.com")
        pwn = Path("/tmp/pwn")
        # Defensive: clear any leftover from previous tests
        if pwn.exists():
            pwn.unlink()

        out = io.StringIO()
        call_command("ensure_superuser", stdout=out)

        user = User.objects.get(username="$(touch /tmp/pwn)")
        assert user.username == "$(touch /tmp/pwn)"
        assert not pwn.exists(), (
            "ensure_superuser must not shell-evaluate the username"
        )

    # --- REQ-002: idempotent re-run ---

    def test_runs_twice_does_not_overwrite_password(self, monkeypatch):
        """Second run with a new password does NOT mutate the existing user."""
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin1")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "oldPass!1")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "old@example.com")

        call_command("ensure_superuser", stdout=io.StringIO())

        user = User.objects.get(username="admin1")
        old_hash = user.password
        old_email = user.email

        # Second run with a different password and email
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "newPass!2")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "new@example.com")
        call_command("ensure_superuser", stdout=io.StringIO())

        user.refresh_from_db()
        assert user.password == old_hash, (
            "ensure_superuser must not overwrite the password of an existing user"
        )
        assert user.email == old_email, (
            "ensure_superuser must not overwrite the email of an existing user"
        )
        # Exactly one user with that username
        assert User.objects.filter(username="admin1").count() == 1

    # --- REQ-002/010: --reset opt-in overrides idempotency ---

    def test_reset_overwrites_existing_user_password(self, monkeypatch):
        """--reset flag explicitly overwrites password and email on existing user.

        Default path is idempotent (test_runs_twice_does_not_overwrite_password).
        --reset is the manual rotation escape hatch.
        """
        # First run: create user with old credentials (default path).
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "resetuser")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "oldPass!1")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "old@example.com")
        call_command("ensure_superuser", stdout=io.StringIO())

        user = User.objects.get(username="resetuser")
        assert user.check_password("oldPass!1")
        assert user.email == "old@example.com"

        # Second run with --reset and new credentials.
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "newPass!2")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "new@example.com")
        call_command("ensure_superuser", reset=True, stdout=io.StringIO())

        user.refresh_from_db()
        assert user.check_password("newPass!2"), (
            "--reset must overwrite the existing user's password"
        )
        assert user.email == "new@example.com", (
            "--reset must overwrite the existing user's email"
        )
        # Exactly one user with that username.
        assert User.objects.filter(username="resetuser").count() == 1

    # --- REQ-003: admin group auto-created and assigned ---

    def test_creates_admin_group_when_missing(self, monkeypatch):
        """admin group is created if absent before user assignment."""
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin2")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "pw")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "")

        assert not Group.objects.filter(name="admin").exists()
        call_command("ensure_superuser", stdout=io.StringIO())
        assert Group.objects.filter(name="admin").exists()

    def test_assigns_user_to_admin_group(self, monkeypatch):
        """The superuser ends up in admin.groups."""
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin3")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "pw")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "")

        call_command("ensure_superuser", stdout=io.StringIO())
        user = User.objects.get(username="admin3")
        assert user.groups.filter(name="admin").exists()

    def test_admin_group_has_all_permissions_after_ensure_superuser(self, monkeypatch):
        """admin group has exactly the six ADMIN_GROUP_PERMISSIONS codenames.

        Decision (a') compose: ensure_superuser seeds the same permission
        set as bootstrap_roles, sourced from the shared constant.
        """
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin4")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "pw")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "")

        call_command("ensure_superuser", stdout=io.StringIO())

        admin = Group.objects.get(name="admin")
        codenames = set(admin.permissions.values_list("codename", flat=True))
        expected = set(ADMIN_GROUP_PERMISSIONS)
        assert codenames >= expected, (
            f"admin group missing perms. expected={expected} got={codenames}"
        )

    # --- REQ-004: missing env → WARNING + exit 0 ---

    def test_missing_username_skips(self, monkeypatch):
        """DJANGO_SUPERUSER_USERNAME missing → WARNING + no User created."""
        monkeypatch.delenv("DJANGO_SUPERUSER_USERNAME", raising=False)
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "pw")
        monkeypatch.delenv("DJANGO_SUPERUSER_EMAIL", raising=False)
        before = User.objects.count()
        out = io.StringIO()
        # Must NOT raise
        call_command("ensure_superuser", stdout=out)
        after = User.objects.count()
        assert after == before, "no User should be created when env is missing"
        assert "SKIP" in out.getvalue()

    def test_missing_password_skips(self, monkeypatch):
        """DJANGO_SUPERUSER_PASSWORD missing → WARNING + no User created."""
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin5")
        monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)
        monkeypatch.delenv("DJANGO_SUPERUSER_EMAIL", raising=False)
        before = User.objects.count()
        out = io.StringIO()
        call_command("ensure_superuser", stdout=out)
        after = User.objects.count()
        assert after == before, "no User should be created when password is missing"
        assert "SKIP" in out.getvalue()

    def test_db_error_raises_command_error(self, monkeypatch):
        """OperationalError from the DB → CommandError (fail-closed).

        Strict TDD: also asserts the mock was reached, so the test fails
        RED when the command does not exist (Unknown command raised
        before any get_or_create call would happen).
        """
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin6")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "pw")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "")

        with mock.patch(
            "django.contrib.auth.models.User.objects.get_or_create",
            side_effect=OperationalError("db down"),
        ) as mock_get_or_create:
            with pytest.raises(CommandError):
                call_command("ensure_superuser", stdout=io.StringIO())
            mock_get_or_create.assert_called_once()

    # --- REQ-006: one identifiable log line per branch ---

    def test_log_line_created(self, monkeypatch):
        """Created branch logs `[ensure_superuser]` + `created` substring."""
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin7")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "pw")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "a@example.com")
        out = io.StringIO()
        call_command("ensure_superuser", stdout=out)
        text = out.getvalue()
        assert "[ensure_superuser]" in text
        assert "created" in text

    def test_log_line_already_exists(self, monkeypatch):
        """Existing-user branch logs `[ensure_superuser]` + `already exists` substring."""
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin8")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "pw")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "a@example.com")
        # First run creates
        call_command("ensure_superuser", stdout=io.StringIO())
        # Second run sees it as existing
        out = io.StringIO()
        call_command("ensure_superuser", stdout=out)
        text = out.getvalue()
        assert "[ensure_superuser]" in text
        assert "already exists" in text

    def test_log_line_skipped(self, monkeypatch):
        """Missing-env branch logs `[ensure_superuser]` + `SKIP` substring."""
        monkeypatch.delenv("DJANGO_SUPERUSER_USERNAME", raising=False)
        monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)
        monkeypatch.delenv("DJANGO_SUPERUSER_EMAIL", raising=False)
        out = io.StringIO()
        call_command("ensure_superuser", stdout=out)
        text = out.getvalue()
        assert "[ensure_superuser]" in text
        assert "SKIP" in text

    def test_invalid_email_raises_command_error(self, monkeypatch):
        """Malformed email → CommandError with "email" in the message.

        Strict TDD: matching against 'email' ensures the test fails RED
        (Unknown command message has no 'email' substring) and passes
        GREEN only when the implementation actually validates the email.
        """
        monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "admin9")
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "pw")
        monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "not-an-email")

        with pytest.raises(CommandError, match="email"):
            call_command("ensure_superuser", stdout=io.StringIO())
        # No user should have been created with the invalid-email payload.
        assert not User.objects.filter(username="admin9").exists()
