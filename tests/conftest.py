"""Tests-level conftest.

Hosts the DB-host fixup required by tests that need a real Postgres
connection. The project's `accessledger/settings_test.py` loads
`.env.test` with `override=True`, which sets POSTGRES_HOST=db (the
docker-compose service name). When tests run outside docker, that
hostname is unresolvable. This conftest rewrites the DB host to
127.0.0.1 at pytest-configure time, BEFORE pytest-django's
`django_db_setup` fixture creates the test database. Production deploy
is unaffected — settings.py (the production settings) still reads
POSTGRES_HOST from env.
"""
import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    from django.conf import settings

    settings.DATABASES["default"]["HOST"] = "127.0.0.1"
