from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        import core.signals  # noqa: F401
        # REQ-AR-007 — register the @register(deploy=True) custom check.
        import accessledger.checks  # noqa: F401
