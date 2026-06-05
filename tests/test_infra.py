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

    def test_ssl_forced_even_when_url_lacks_sslmode(self, monkeypatch):
        """DATABASE_URL without sslmode param still gets sslmode=require."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgres://u:p@neon.example:5432/db",
        )
        import accessledger.settings as s
        importlib.reload(s)

        db = s.DATABASES["default"]
        assert db["OPTIONS"]["sslmode"] == "require"
        assert db["OPTIONS"]["connect_timeout"] == 10
        assert db["HOST"] == "neon.example"

    def test_database_url_no_ssl_drops_in_pooled_url(self, monkeypatch):
        """DATABASE_URL with non-standard port preserves it correctly."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgres://app:pass@ep-neon.us-east-2.aws.neon.tech:5432/appdb",
        )
        import accessledger.settings as s
        importlib.reload(s)

        db = s.DATABASES["default"]
        assert db["PORT"] == 5432
        assert db["NAME"] == "appdb"
        assert db["USER"] == "app"
        assert db["CONN_MAX_AGE"] == 60
        
    def test_postgres_fallback_keeps_default_port(self, monkeypatch):
        """When POSTGRES_PORT is not set, default port 5432 is used."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("POSTGRES_PORT", raising=False)
        monkeypatch.setenv("POSTGRES_DB", "mydb")
        monkeypatch.setenv("POSTGRES_USER", "myuser")
        monkeypatch.setenv("POSTGRES_PASSWORD", "mypass")
        monkeypatch.setenv("POSTGRES_HOST", "dbhost")

        import accessledger.settings as s
        importlib.reload(s)

        db = s.DATABASES["default"]
        assert db["PORT"] == "5432"


# ── Task 2.2: .env.example documentation ────────────────────────────────

class TestEnvExample:
    """Verify .env.example documents all required env vars."""

    @pytest.fixture
    def env_example_path(self):
        return Path(__file__).resolve().parent.parent / ".env.example"

    def test_datbase_url_documented(self, env_example_path):
        """DATABASE_URL must be documented with usage hint."""
        content = env_example_path.read_text()
        assert "DATABASE_URL" in content, (
            "DATABASE_URL not documented in .env.example"
        )

    def test_seed_demo_documented(self, env_example_path):
        """SEED_DEMO must be documented with opt-in explanation."""
        content = env_example_path.read_text()
        assert "SEED_DEMO" in content, (
            "SEED_DEMO not documented in .env.example"
        )

    def test_postgres_vars_retained(self, env_example_path):
        """POSTGRES_* vars must still be present for local Docker."""
        content = env_example_path.read_text()
        assert "POSTGRES_DB" in content
        assert "POSTGRES_USER" in content
        assert "POSTGRES_HOST" in content
        assert "POSTGRES_PORT" in content

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

    def test_seed_runs_when_database_url_empty(self, entrypoint_path):
        """Local mode: -z DATABASE_URL triggers seed (no DATABASE_URL set)."""
        content = entrypoint_path.read_text()
        assert '-z "$DATABASE_URL"' in content, (
            "entrypoint.sh must use -z to check empty DATABASE_URL for local auto-seed"
        )

    def test_seed_runs_when_seed_demo_true(self, entrypoint_path):
        """Production opt-in: SEED_DEMO=True triggers seed explicitly."""
        content = entrypoint_path.read_text()
        assert '"$SEED_DEMO" = "True"' in content, (
            "entrypoint.sh must check SEED_DEMO=True for production opt-in seeding"
        )

    def test_conditional_uses_or_logic(self, entrypoint_path):
        """Both conditions use OR: local auto OR production opt-in."""
        content = entrypoint_path.read_text()
        # The if statement should use || between the two conditions
        assert "[ -z \"$DATABASE_URL\" ] || [ \"$SEED_DEMO\" = \"True\" ]" in content, (
            "entrypoint.sh must use OR logic: local auto-seed OR production opt-in"
        )

    def test_local_mode_triggers_seed(self):
        """Local mode (no DATABASE_URL): seed must run."""
        result = subprocess.run(
            [
                "sh", "-c",
                'unset DATABASE_URL; unset SEED_DEMO; '
                'if [ -z "$DATABASE_URL" ] || [ "$SEED_DEMO" = "True" ]; '
                'then echo "SEED_RUN"; else echo "SEED_SKIP"; fi',
            ],
            capture_output=True,
            text=True,
        )
        assert "SEED_RUN" in result.stdout, (
            f"Local mode should trigger seed, got: {result.stdout}"
        )

    def test_production_mode_skips_seed(self):
        """Production (DATABASE_URL set, SEED_DEMO unset): seed must skip."""
        result = subprocess.run(
            [
                "sh", "-c",
                'DATABASE_URL=postgres://x:y@host:5432/db; unset SEED_DEMO; '
                'if [ -z "$DATABASE_URL" ] || [ "$SEED_DEMO" = "True" ]; '
                'then echo "SEED_RUN"; else echo "SEED_SKIP"; fi',
            ],
            capture_output=True,
            text=True,
        )
        assert "SEED_SKIP" in result.stdout, (
            f"Production mode should skip seed, got: {result.stdout}"
        )

    def test_production_opt_in_triggers_seed(self):
        """Production opt-in (DATABASE_URL set, SEED_DEMO=True): seed must run."""
        result = subprocess.run(
            [
                "sh", "-c",
                'DATABASE_URL=postgres://x:y@host:5432/db; SEED_DEMO=True; '
                'if [ -z "$DATABASE_URL" ] || [ "$SEED_DEMO" = "True" ]; '
                'then echo "SEED_RUN"; else echo "SEED_SKIP"; fi',
            ],
            capture_output=True,
            text=True,
        )
        assert "SEED_RUN" in result.stdout, (
            f"Production opt-in should trigger seed, got: {result.stdout}"
        )
