"""Test settings for accessledger.

REQ-AR-007 — CRITICAL import-order rule (must land with Task 4.1):

    1. ``os.environ.setdefault("SECRET_KEY", ...)`` and ``ALLOWED_HOSTS``
       MUST run BEFORE ``from .settings import *``.
    2. ``from .settings import *`` triggers settings.py module-load,
       which now uses ``os.environ["SECRET_KEY"]`` (dict-access raises
       KeyError on missing env var).
    3. Without pre-seeding, pytest collection would crash with KeyError.

``IS_TEST_SETTINGS = True`` is set AFTER the wildcard import so the
custom @register(deploy=True) check in ``accessledger.checks`` can
detect test settings and return early.
"""
import os

# Pre-seed SECRET_KEY before settings.py is evaluated.
# 60+ chars to pass the Layer B length check (REQ-AR-007 7.7).
os.environ.setdefault(
    "SECRET_KEY",
    "django-insecure-test-key-ci-only" + "-x" * 30,  # 60+ chars total
)
# Pre-seed ALLOWED_HOSTS so DEBUG=False settings still load.
os.environ.setdefault("ALLOWED_HOSTS", "testserver,localhost")

from .settings import *  # noqa: E402,F401,F403  (must come after setdefault)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(BASE_DIR / ".env.test", override=False)  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "accessledger",
        "USER": os.getenv("POSTGRES_USER", "danidev_dj"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AXES_ENABLED = False

# REQ-AR-007 Scenario 7.5 — flag inspected by accessledger.checks
# security_custom_check. When True, the deploy check returns early so
# the 60-char test key isn't flagged.
IS_TEST_SETTINGS = True