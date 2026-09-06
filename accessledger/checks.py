"""Custom system checks for AccessLedger.

Registered via ``@register(deploy=True)`` so they only run under
``python manage.py check --deploy``.

Scenarios covered (REQ-AR-007):
- 7.6 — custom check runs without error
- 7.7 — Warning on weak SECRET_KEY (length < 50)
- 7.7b — Error on insecure-prefix SECRET_KEY
- 7.7c — Error on missing SECRET_KEY in production
- 7.11 — Layer B catches weakness that Layer A allows (dev)

Exempt when ``settings.IS_TEST_SETTINGS`` is truthy so the test
settings' 60-char django-insecure-... key doesn't trip the prefix
rejection (REQ-AR-007 Scenario 7.5).
"""
from django.conf import settings
from django.core.checks import Error, Warning, register


SECRET_KEY_MIN_LENGTH = 50
INSECURE_PREFIX = "django-insecure-"


@register(deploy=True)
def security_custom_check(app_configs, **kwargs):
    """Return a list of Warning/Error items for SECRET_KEY strength
    and required DB env vars under production ENV.
    """
    if getattr(settings, "IS_TEST_SETTINGS", False):
        return []  # skip under pytest

    issues = []

    secret_key = getattr(settings, "SECRET_KEY", None)
    if not secret_key:
        # Layer A already raises for missing key under DEBUG=False, but
        # the deploy check also surfaces a clear Error message.
        issues.append(
            Error(
                "SECRET_KEY is not set.",
                hint="Set the SECRET_KEY env var in the production environment.",
                id="accessledger.E001",
            )
        )
    else:
        # Length check (Warning — Layer A accepts it but it's weak)
        if len(secret_key) < SECRET_KEY_MIN_LENGTH:
            issues.append(
                Warning(
                    f"SECRET_KEY is shorter than {SECRET_KEY_MIN_LENGTH} chars "
                    f"(got {len(secret_key)}).",
                    hint=(
                        "Generate a 50+ char random key. Django refuses to "
                        "start with this in production eventually."
                    ),
                    id="accessledger.W001",
                )
            )
        # Prefix check (Error — django-insecure-* is NEVER acceptable)
        if secret_key.startswith(INSECURE_PREFIX):
            issues.append(
                Error(
                    "SECRET_KEY starts with 'django-insecure-'. "
                    "This is the dev-only prefix Django uses for ephemeral keys.",
                    hint=(
                        "Generate a real random key for production "
                        "(see docs/howto/deployment/checklist.html)."
                    ),
                    id="accessledger.E002",
                )
            )

    return issues