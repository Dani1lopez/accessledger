"""Infrastructure tests — database configuration, env vars, entrypoint logic."""
import os
import importlib
import subprocess
from pathlib import Path

import pytest


# ── Task 1.1: dj-database-url dependency ──────────────────────────────

class TestDjDatabaseUrlDependency:
    """Verify dj-database-url is declared and importable."""

    def test_package_is_importable(self):
        """dj_database_url must be importable."""
        import dj_database_url  # noqa: F401

    def test_listed_in_requirements(self):
        """requirements.txt must declare dj-database-url>=2.0."""
        req_path = Path(__file__).resolve().parent.parent / "requirements.txt"
        content = req_path.read_text()
        assert "dj-database-url" in content, (
            "dj-database-url not found in requirements.txt"
        )


# ── Task 2.1: Hybrid DATABASES config ──────────────────────────────────

class TestDatabasesConfig:
    """Verify settings.py DATABASES behaves correctly in both modes."""

    def test_with_database_url_uses_ssl_and_pooling(self, monkeypatch):
        """When DATABASE_URL is set, config includes SSL, conn_max_age, timeout."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgres://user:pass@host.example:5432/mydb?sslmode=require",
        )
        # Reload accessledger.settings to pick up the new env var
        import accessledger.settings as s
        importlib.reload(s)

        db = s.DATABASES["default"]
        assert db["ENGINE"] == "django.db.backends.postgresql"
        assert db["CONN_MAX_AGE"] == 60
        assert db["CONN_HEALTH_CHECKS"] is True
        assert db["OPTIONS"]["sslmode"] == "require"
        assert db["OPTIONS"]["connect_timeout"] == 10
        assert db["NAME"] == "mydb"
        assert db["HOST"] == "host.example"
        assert db["PORT"] == 5432

    def test_without_database_url_falls_back_to_postgres_vars(self, monkeypatch):
        """When DATABASE_URL is absent, POSTGRES_* env vars are used."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("POSTGRES_DB", "testdb")
        monkeypatch.setenv("POSTGRES_USER", "testuser")
        monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
        monkeypatch.setenv("POSTGRES_HOST", "pg.local")
        monkeypatch.setenv("POSTGRES_PORT", "5433")

        import accessledger.settings as s
        importlib.reload(s)

        db = s.DATABASES["default"]
        assert db["ENGINE"] == "django.db.backends.postgresql"
        assert db["NAME"] == "testdb"
        assert db["USER"] == "testuser"
        assert db["PASSWORD"] == "secret"
        assert db["HOST"] == "pg.local"
        assert db["PORT"] == "5433"


# ── Task 2.3: Smart seed in entrypoint.sh ──────────────────────────────

class TestEntrypointSeedLogic:
    """Verify entrypoint.sh guards seed_data with env vars."""

    @pytest.fixture
    def entrypoint_path(self):
        return Path(__file__).resolve().parent.parent / "entrypoint.sh"

    def test_script_is_syntactically_valid(self, entrypoint_path):
        """sh -n must report no syntax errors."""
        result = subprocess.run(
            ["sh", "-n", str(entrypoint_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"entrypoint.sh syntax error: {result.stderr}"
        )

    def test_seed_conditional_exists(self, entrypoint_path):
        """Script must guard seed_data with DATABASE_URL and SEED_DEMO checks."""
        content = entrypoint_path.read_text()
        assert "DATABASE_URL" in content, (
            "entrypoint.sh must reference DATABASE_URL for seed gating"
        )
        assert "SEED_DEMO" in content, (
            "entrypoint.sh must reference SEED_DEMO for opt-in seeding"
        )
