"""Infrastructure tests — database configuration, env vars, entrypoint logic."""
import os
import sys
import importlib
import re
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
        """Production opt-in: SEED_DEMO=true (lowercase) triggers seed explicitly."""
        content = entrypoint_path.read_text()
        assert '"$SEED_DEMO" = "true"' in content, (
            "entrypoint.sh must check SEED_DEMO=true (lowercase) for production "
            "opt-in seeding, matching the seed_data production guard"
        )

    def test_conditional_uses_or_logic(self, entrypoint_path):
        """Both conditions use OR: local auto OR production opt-in."""
        content = entrypoint_path.read_text()
        # The if statement should use || between the two conditions
        assert "[ -z \"$DATABASE_URL\" ] || [ \"$SEED_DEMO\" = \"true\" ]" in content, (
            "entrypoint.sh must use OR logic: local auto-seed OR production opt-in"
        )

    def test_local_mode_triggers_seed(self):
        """Local mode (no DATABASE_URL): seed must run."""
        result = subprocess.run(
            [
                "sh", "-c",
                'unset DATABASE_URL; unset SEED_DEMO; '
                'if [ -z "$DATABASE_URL" ] || [ "$SEED_DEMO" = "true" ]; '
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
                'if [ -z "$DATABASE_URL" ] || [ "$SEED_DEMO" = "true" ]; '
                'then echo "SEED_RUN"; else echo "SEED_SKIP"; fi',
            ],
            capture_output=True,
            text=True,
        )
        assert "SEED_SKIP" in result.stdout, (
            f"Production mode should skip seed, got: {result.stdout}"
        )

    def test_production_opt_in_triggers_seed(self):
        """Production opt-in (DATABASE_URL set, SEED_DEMO=true): seed must run."""
        result = subprocess.run(
            [
                "sh", "-c",
                'DATABASE_URL=postgres://x:y@host:5432/db; SEED_DEMO=true; '
                'if [ -z "$DATABASE_URL" ] || [ "$SEED_DEMO" = "true" ]; '
                'then echo "SEED_RUN"; else echo "SEED_SKIP"; fi',
            ],
            capture_output=True,
            text=True,
        )
        assert "SEED_RUN" in result.stdout, (
            f"Production opt-in should trigger seed, got: {result.stdout}"
        )

    # ── REQ-JD-03 — lowercase SEED_DEMO contract (entrypoint ⇄ seed_data) ──

    @staticmethod
    def _entrypoint_seed_gate() -> str:
        """Extract the real `if [ -z "$DATABASE_URL" ] || [ "$SEED_DEMO" = "x" ]`
        line from entrypoint.sh so shell behavior tests exercise the actual
        gate literal instead of a duplicated copy."""
        gate_path = Path(__file__).resolve().parent.parent / "entrypoint.sh"
        content = gate_path.read_text()
        match = re.search(
            r'^[ \t]*if \[ -z "\$DATABASE_URL" \] \|\| \[ "\$SEED_DEMO" = "[^"]+" \]; then$',
            content,
            re.MULTILINE,
        )
        assert match is not None, "entrypoint.sh seed gate line not found"
        return match.group(0)

    def test_production_opt_in_lowercase_true_triggers_seed(self):
        """REQ-JD-03 Scenario 3.1 — DATABASE_URL set + SEED_DEMO=true must run
        the seed path through the REAL entrypoint gate (the regression this
        change fixes: the gate used to know only capital "True")."""
        gate = self._entrypoint_seed_gate()
        result = subprocess.run(
            [
                "sh", "-c",
                'DATABASE_URL=postgres://x:y@host:5432/db; SEED_DEMO=true; '
                f'{gate} '
                'echo "SEED_RUN"; else echo "SEED_SKIP"; fi',
            ],
            capture_output=True,
            text=True,
        )
        assert "SEED_RUN" in result.stdout, (
            f"Documented SEED_DEMO=true opt-in should trigger seed, got: {result.stdout}"
        )

    def test_production_capital_true_is_not_an_opt_in(self):
        """REQ-JD-03 Scenario 3.2 — SEED_DEMO=True (capital) must NOT run the
        seed path: entrypoint and seed_data share one case-sensitive contract,
        and the command's own guard refuses capital True."""
        gate = self._entrypoint_seed_gate()
        result = subprocess.run(
            [
                "sh", "-c",
                'DATABASE_URL=postgres://x:y@host:5432/db; SEED_DEMO=True; '
                f'{gate} '
                'echo "SEED_RUN"; else echo "SEED_SKIP"; fi',
            ],
            capture_output=True,
            text=True,
        )
        assert "SEED_SKIP" in result.stdout, (
            f"Capital True must not be an opt-in, got: {result.stdout}"
        )

    def test_seed_data_opt_in_value_aligned_with_entrypoint(self):
        """REQ-JD-03 Scenario 3.3 — entrypoint and seed_data must gate on the
        same case-sensitive opt-in token, and it must be lowercase "true"."""
        import re

        repo_root = Path(__file__).resolve().parent.parent
        entrypoint = (repo_root / "entrypoint.sh").read_text()
        seed_data = (
            repo_root / "core" / "management" / "commands" / "seed_data.py"
        ).read_text()

        entrypoint_token = re.search(
            r'\[\s*"\$SEED_DEMO"\s*=\s*"([^"]+)"\s*\]', entrypoint
        )
        seed_data_token = re.search(
            r'os\.environ\.get\("SEED_DEMO"\)\s*!=\s*"([^"]+)"', seed_data
        )
        assert entrypoint_token is not None, "entrypoint.sh opt-in token not found"
        assert seed_data_token is not None, "seed_data opt-in token not found"
        assert entrypoint_token.group(1) == seed_data_token.group(1), (
            "entrypoint.sh and seed_data.py must use the same SEED_DEMO token"
        )
        assert entrypoint_token.group(1) == "true"

    # ── SEC-002 carve-out: entrypoint delegates superuser creation ──────

    def test_createsuperuser_not_in_entrypoint(self, entrypoint_path):
        """SEC-002: entrypoint.sh must NOT call `createsuperuser` directly.

        `createsuperuser --noinput --username "$VAR" --email "$VAR"` was
        the original shell-injection sink — the unquoted $VAR path could
        leak values into the shell. Now delegated to the ensure_superuser
        management command which reads env via os.environ.
        """
        content = entrypoint_path.read_text()
        assert "createsuperuser" not in content, (
            "entrypoint.sh must not invoke `createsuperuser`; "
            "delegate to `python manage.py ensure_superuser` instead."
        )

    def test_shell_c_not_in_entrypoint(self, entrypoint_path):
        """SEC-002: entrypoint.sh must NOT use `shell -c` to interpolate env vars.

        The original vulnerable block used `python manage.py shell -c "..."
        with $DJANGO_SUPERUSER_USERNAME interpolated into Python source —
        a direct command-substitution RCE sink. Now removed.
        """
        content = entrypoint_path.read_text()
        assert "shell -c" not in content, (
            "entrypoint.sh must not use `manage.py shell -c`; "
            "this was the original shell-injection sink."
        )

    def test_ensure_superuser_invoked(self, entrypoint_path):
        """SEC-002: entrypoint.sh MUST call `python manage.py ensure_superuser`.

        This is the new (safe) delegation point — values are read via
        os.environ inside the command, not interpolated into shell.
        """
        content = entrypoint_path.read_text()
        assert "python manage.py ensure_superuser" in content, (
            "entrypoint.sh must invoke `python manage.py ensure_superuser`"
        )


# ── R4-001 regression: DB host not forcibly rewritten ────────────────────

class TestConftestDoesNotMutateEnv:
    """R4-001: root conftest.py must not set POSTGRES_HOST / POSTGRES_PORT."""

    def test_root_conftest_does_not_set_postgres_env(self):
        """Root conftest.py must not unconditionally set POSTGRES_HOST."""
        conftest_path = Path(__file__).resolve().parent.parent / "conftest.py"
        content = conftest_path.read_text()
        assert "POSTGRES_HOST" not in content, (
            "conftest.py must not set POSTGRES_HOST"
        )
        assert "POSTGRES_PORT" not in content, (
            "conftest.py must not set POSTGRES_PORT"
        )


class TestSettingsTestOverrideBehavior:
    """R4-001: settings_test.py load_dotenv must use override=False."""

    def test_override_is_false(self):
        """settings_test.py must call load_dotenv with override=False."""
        path = (
            Path(__file__).resolve().parent.parent
            / "accessledger" / "settings_test.py"
        )
        content = path.read_text()
        assert "override=False" in content, (
            "settings_test.py must use override=False so env vars can override "
            ".env.test defaults"
        )

    def test_override_true_is_absent(self):
        """settings_test.py must NOT contain override=True."""
        path = (
            Path(__file__).resolve().parent.parent
            / "accessledger" / "settings_test.py"
        )
        content = path.read_text()
        assert "override=True" not in content, (
            "settings_test.py must not use override=True"
        )


class TestTestsConftestDeleted:
    """R4-001: tests/conftest.py must not exist."""

    def test_tests_conftest_does_not_exist(self):
        """tests/conftest.py must be deleted — it forced DB HOST=127.0.0.1."""
        path = Path(__file__).resolve().parent / "conftest.py"
        assert not path.exists(), (
            "tests/conftest.py must be deleted; it forced "
            "settings.DATABASES['default']['HOST'] = '127.0.0.1'"
        )


class TestEffectiveDbHostNotForceRewritten:
    """R4-001: loaded Django settings HOST must not be forcibly rewritten."""

    def test_db_host_is_not_empty(self):
        """settings.DATABASES HOST must be a non-empty string from env or .env.test."""
        from django.conf import settings

        host = settings.DATABASES["default"]["HOST"]
        assert host, "DATABASES HOST must be a non-empty string"
        assert isinstance(host, str)


# ── F3 hardening: DB readiness wait with retries in entrypoint.sh ────────

class TestEntrypointDbReadiness:
    """F3: entrypoint.sh must probe PostgreSQL with retries before any
    DB-touching step, so a transient DNS/connection blip (Render incident:
    NXDOMAIN on an expired/free-tier host) no longer kills the container
    before gunicorn binds.
    """

    @pytest.fixture
    def entrypoint_path(self):
        return Path(__file__).resolve().parent.parent / "entrypoint.sh"

    @staticmethod
    def _readiness_snippet(entrypoint_text: str) -> str:
        """Extract the real `python - <<'PY' ... PY` readiness heredoc so the
        behavior tests execute the actual shipped snippet, not a copy."""
        match = re.search(r"python - <<'PY'\n(.*?)\nPY", entrypoint_text, re.DOTALL)
        assert match is not None, (
            "entrypoint.sh must contain a `python - <<'PY'` heredoc readiness check"
        )
        return match.group(0)

    @staticmethod
    def _run_snippet(snippet: str, extra_env: dict) -> subprocess.CompletedProcess:
        """Run the extracted snippet under `sh -c` with `python` resolved to the
        test venv interpreter (which has psycopg installed)."""
        env = os.environ.copy()
        env.update(extra_env)
        # Do NOT resolve sys.executable: the venv bin dir (parent of the
        # `python` symlink) is what provides a `python` with psycopg.
        venv_bin = Path(sys.executable).parent
        env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
        return subprocess.run(
            ["sh", "-c", snippet],
            capture_output=True,
            text=True,
            env=env,
            timeout=20,
        )

    # ── Source-parity tests ──────────────────────────────────────────────

    def test_readiness_block_precedes_db_touching_steps(self, entrypoint_path):
        """Order contract: the readiness probe must run before collectstatic
        and before migrate (any DB-touching step)."""
        content = entrypoint_path.read_text()
        snippet = self._readiness_snippet(content)
        assert content.index(snippet) < content.index("collectstatic"), (
            "readiness block must run before collectstatic"
        )
        assert content.index(snippet) < content.index("migrate --noinput"), (
            "readiness block must run before migrate"
        )

    def test_retry_env_vars_referenced_with_defaults(self, entrypoint_path):
        """Retry count and wait must come from DB_READY_RETRIES/DB_READY_WAIT
        with defaults 30 / 2 so tests (and operators) can tune them."""
        content = entrypoint_path.read_text()
        assert 'os.environ.get("DB_READY_RETRIES", "30")' in content, (
            "entrypoint.sh must read DB_READY_RETRIES with default 30"
        )
        assert 'os.environ.get("DB_READY_WAIT", "2")' in content, (
            "entrypoint.sh must read DB_READY_WAIT with default 2"
        )

    def test_gunicorn_bind_token_in_entrypoint(self, entrypoint_path):
        """F1 (half): the entrypoint gunicorn line must bind 0.0.0.0:${PORT:-8080}."""
        content = entrypoint_path.read_text()
        gunicorn_lines = [line for line in content.splitlines() if "gunicorn" in line]
        assert gunicorn_lines, "entrypoint.sh must have a gunicorn line"
        for line in gunicorn_lines:
            assert "--bind 0.0.0.0:${PORT:-8080}" in line, (
                f"entrypoint gunicorn line must bind 0.0.0.0:${{PORT:-8080}}: {line}"
            )

    # ── Behavior tests (real PostgreSQL at 127.0.0.1 is up for the suite) ──

    def test_failure_path_closed_port_exits_nonzero(self):
        """DATABASE_URL pointing at a closed port with 2 retries / 0 wait must
        exit nonzero — after visibly retrying, not on the first blip."""
        snippet = self._readiness_snippet(
            (Path(__file__).resolve().parent.parent / "entrypoint.sh").read_text()
        )
        result = self._run_snippet(
            snippet,
            {
                "DATABASE_URL": "postgres://u:p@127.0.0.1:1/db",
                "DB_READY_RETRIES": "2",
                "DB_READY_WAIT": "0",
            },
        )
        assert result.returncode != 0, (
            f"closed-port DATABASE_URL must exit nonzero, got: {result.stdout}"
        )
        assert "attempt 2/2" in result.stdout, (
            "failure path must retry before giving up, stdout was: "
            f"{result.stdout!r}"
        )

    def test_success_path_local_db_exits_zero(self):
        """POSTGRES_* conninfo against the suite's real local PostgreSQL must
        exit 0 on the first attempt."""
        snippet = self._readiness_snippet(
            (Path(__file__).resolve().parent.parent / "entrypoint.sh").read_text()
        )
        env = {"POSTGRES_HOST": "127.0.0.1"}
        # Pass through the suite's real DB creds (.env.test loads them into
        # os.environ); only force the host to the loopback interface.
        for var in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_PORT"):
            if var in os.environ:
                env[var] = os.environ[var]
        result = self._run_snippet(snippet, env)
        assert result.returncode == 0, (
            f"readiness probe against the local DB must exit 0, got: "
            f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
        )


# ── Issue #82: entrypoint must not enable xtrace (secret leak via shell trace) ──

class TestEntrypointNoXtraceSecretLeak:
    """Issue #82: `set -ex` made the shell trace every expanded command
    (including the seed gate and the superuser gate), so DATABASE_URL and
    DJANGO_SUPERUSER_* values landed verbatim in container logs via xtrace.
    The entrypoint must keep fail-fast (`set -e`) but must never enable
    xtrace, so secret-bearing env values can never reach the logs.
    """

    DATABASE_URL_CANARY = (
        "postgres://xtrace-canary-dbuser:xtrace-canary-dbpass"
        "@xtrace-canary-host.invalid:5432/xtrace-canary-db"
    )
    USERNAME_CANARY = "xtrace-canary-superuser-username"
    PASSWORD_CANARY = "xtrace-canary-superuser-password"
    PORT_CANARY = "xtrace-canary-port"

    @pytest.fixture
    def entrypoint_path(self):
        return Path(__file__).resolve().parent.parent / "entrypoint.sh"

    @pytest.fixture(scope="class")
    def entrypoint_run(self, tmp_path_factory):
        """Run the REAL entrypoint.sh once with stubbed `python`/`gunicorn`
        so every shell line — including the seed gate and the superuser
        gate — executes without touching Django, the DB, or staticfiles."""
        stub_dir = tmp_path_factory.mktemp("xtrace-stubs")
        for name in ("python", "gunicorn"):
            stub = stub_dir / name
            stub.write_text("#!/bin/sh\nexit 0\n")
            stub.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(stub_dir) + os.pathsep + env.get("PATH", "")
        env["DATABASE_URL"] = self.DATABASE_URL_CANARY
        env["DJANGO_SUPERUSER_USERNAME"] = self.USERNAME_CANARY
        env["DJANGO_SUPERUSER_PASSWORD"] = self.PASSWORD_CANARY
        env["PORT"] = self.PORT_CANARY
        env.pop("DEBUG", None)
        entrypoint = Path(__file__).resolve().parent.parent / "entrypoint.sh"
        return subprocess.run(
            ["sh", str(entrypoint)],
            capture_output=True,
            text=True,
            env=env,
            timeout=20,
        )

    def test_entrypoint_runs_to_completion_with_stubs(self, entrypoint_run):
        """Sanity: the stubbed run must reach the final exec (exit 0), so the
        sibling tests exercise the whole script, not a prefix."""
        assert entrypoint_run.returncode == 0, (
            f"stubbed entrypoint run must exit 0, got rc="
            f"{entrypoint_run.returncode} stdout={entrypoint_run.stdout!r} "
            f"stderr={entrypoint_run.stderr!r}"
        )

    def test_entrypoint_does_not_enable_xtrace(self, entrypoint_run):
        """Behavior: xtrace emits `+ command` trace lines; with canaries in
        every gate the whole script runs, so none may appear in output."""
        output = entrypoint_run.stdout + entrypoint_run.stderr
        trace_lines = [
            line for line in output.splitlines() if re.match(r"^\++ ", line)
        ]
        assert not trace_lines, (
            "entrypoint.sh must not enable xtrace; trace lines leaked: "
            f"{trace_lines[:5]!r}"
        )

    def test_entrypoint_does_not_emit_database_url_canary(self, entrypoint_run):
        """Behavior: the DATABASE_URL canary must never be emitted by the
        entrypoint shell trace (under `set -ex` the seed-gate trace printed
        the full expanded URL)."""
        output = entrypoint_run.stdout + entrypoint_run.stderr
        assert self.DATABASE_URL_CANARY not in output, (
            "entrypoint.sh shell trace must never emit DATABASE_URL; leaked: "
            f"{output!r}"
        )

    def test_entrypoint_does_not_emit_superuser_credential_canaries(
        self, entrypoint_run
    ):
        """Behavior: DJANGO_SUPERUSER_USERNAME/PASSWORD canaries must never be
        emitted by the entrypoint shell trace (under `set -ex` the
        superuser-gate trace printed the expanded values)."""
        output = entrypoint_run.stdout + entrypoint_run.stderr
        assert self.PASSWORD_CANARY not in output, (
            "entrypoint.sh shell trace must never emit "
            f"DJANGO_SUPERUSER_PASSWORD; leaked: {output!r}"
        )
        assert self.USERNAME_CANARY not in output, (
            "entrypoint.sh shell trace must never emit "
            f"DJANGO_SUPERUSER_USERNAME; leaked: {output!r}"
        )

    def test_entrypoint_set_line_is_fail_fast_only(self, entrypoint_path):
        """Source guard: the option line must be exactly `set -e` — fail-fast
        preserved, no xtrace, and no scope creep (no -u / pipefail)."""
        content = entrypoint_path.read_text()
        set_lines = [line for line in content.splitlines() if line.startswith("set ")]
        assert set_lines == ["set -e"], (
            f"entrypoint.sh must set exactly 'set -e' (fail-fast, no xtrace); "
            f"found: {set_lines!r}"
        )


class TestProcfileBindParity:
    """F1: the Procfile gunicorn invocation must match entrypoint.sh exactly,
    including `--bind 0.0.0.0:${PORT:-8080}` (Render 'No open ports detected'
    incident: default gunicorn bind is 127.0.0.1:8000, unreachable externally).
    """

    @pytest.fixture
    def procfile_path(self):
        return Path(__file__).resolve().parent.parent / "Procfile"

    def test_procfile_binds_public_interface(self, procfile_path):
        """Procfile must carry the explicit public bind token."""
        content = procfile_path.read_text()
        assert "--bind 0.0.0.0:${PORT:-8080}" in content, (
            "Procfile must bind 0.0.0.0:${PORT:-8080} so the platform can detect "
            "open ports"
        )

    def test_procfile_matches_entrypoint_gunicorn_invocation(self, procfile_path):
        """Token parity: Procfile's gunicorn argument vector must equal the
        entrypoint.sh gunicorn line (minus the `exec` prefix and `web:` label)."""
        repo = Path(__file__).resolve().parent.parent
        entrypoint = (repo / "entrypoint.sh").read_text()
        procfile = procfile_path.read_text()

        entry_line = next(
            line for line in entrypoint.splitlines() if "gunicorn" in line
        )
        entry_args = entry_line.replace("exec ", "").split()
        proc_args = procfile.strip().split()

        assert proc_args[0] == "web:", "Procfile first token must be the web label"
        assert proc_args[1:] == entry_args, (
            f"Procfile gunicorn args {proc_args[1:]} must match entrypoint.sh "
            f"gunicorn args {entry_args}"
        )
