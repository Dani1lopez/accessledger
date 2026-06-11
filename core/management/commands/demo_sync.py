"""Manual demo command for the V2 adapter skeleton.

Prints a ``DEMO / no-op`` banner. NO external I/O or DB writes.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from core.adapters import registry
from core.adapters.demo import DemoAdapter  # noqa: F401 — triggers @register


DEFAULT_ADAPTER_PATH = f"{DemoAdapter.__module__}.{DemoAdapter.__qualname__}"


class Command(BaseCommand):
    help = "Run a demo adapter sync (DEMO / no-op — no real I/O)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--adapter", default=DEFAULT_ADAPTER_PATH,
                            help="Dotted path of a registered adapter to run.")

    def handle(self, *args, **options) -> None:
        adapter_path: str = options["adapter"]
        try:
            adapter = registry.get_adapter(adapter_path)
        except registry.AdapterLookupError as exc:
            raise CommandError(str(exc)) from exc

        result = adapter.sync()
        self.stdout.write(f"adapter: {adapter_path}")
        self.stdout.write(f"ok: {result.ok}")
        self.stdout.write(f"detail: {result.detail}")
        self.stdout.write("DEMO / no-op — no external I/O was performed.")
        if not result.ok:
            raise CommandError(f"Adapter {adapter_path} reported failure: {result.detail}")
