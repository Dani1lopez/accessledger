# External Service Adapters — Contract (V2 Skeleton)

The V2 adapter layer is a **skeleton only**: it defines the shape of a future integration with external services, without performing any real I/O or shipping a live integration.

> **TL;DR.** `ResourceAdapter` is an ABC with one method (`sync()`). Adapters are whitelisted through a module-level registry. The `DemoAdapter` and the `demo_sync` management command are explicit **no-op** demonstration helpers. Nothing here talks to the network, the database, or a real provider.

## Why this exists

V2 work is a foundation: it makes it possible to describe — and one day integrate with — external services (repos, VPNs, SaaS dashboards) without breaking the current application surface. The skeleton establishes the **adapter contract**, the **registry**, an **explicit no-op demo**, and the **non-goals** so future readers cannot mistake the skeleton for a working integration.

## The contract
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class SyncResult:
    ok: bool
    detail: str = ""

class ResourceAdapter(ABC):
    @abstractmethod
    def sync(self) -> SyncResult:
        ...
```
- `sync()` returns a `SyncResult` describing success or failure.
- Adapters are synchronous, in-memory, and side-effect-free.
- `SyncResult` is a **frozen** dataclass; it is not mutable.

## The registry
```python
from core.adapters import register, get_adapter

@register
class MyAdapter(ResourceAdapter):
    def sync(self) -> SyncResult:
        return SyncResult(ok=True, detail="ok")

adapter = get_adapter("core.adapters.demo.DemoAdapter")
```
Hard rules enforced by the registry:

1. Only classes decorated with `@register` and that subclass `ResourceAdapter` are resolvable.
2. `get_adapter` **never** calls `importlib`. Unregistered targets are rejected with `AdapterLookupError` even when the path is importable by other means.
3. The storage key is the class's fully-qualified dotted path (`module.qualname`); no aliasing, no DB-stored path, no settings-driven config.

> **Foot-gun warning.** `importlib.import_string` is intentionally NOT used at the resolution site. A future contributor who adds it "to be helpful" reintroduces a code-execution surface the registry was designed to remove.

## The demo
```python
@register
class DemoAdapter(ResourceAdapter):
    def sync(self) -> SyncResult:
        return SyncResult(ok=True, detail="DEMO / no-op")
```
- `DemoAdapter` returns success without any work.
- The literal string `DEMO / no-op` is part of the contract: the demo must identify itself as a non-production placeholder.
- There is no "real" demo, no stub provider, and no flag to flip the demo into a live adapter. A real adapter is a future SDD change.

## The management command
```
python manage.py demo_sync                          # default: runs the demo
python manage.py demo_sync --adapter core.adapters.demo.DemoAdapter
```
- Default invocation: prints a `DEMO / no-op` banner, exits 0.
- Unknown `--adapter`: prints a `CommandError`, exits non-zero.
- The command does not import arbitrary targets; the registry's whitelist is the only source of admissible adapter paths.

## What this is NOT

This skeleton is intentionally **not**: a live GitHub / VPN / SaaS integration; a scheduled job (no Celery beat, no cron, no signal-based retry loop); a database-backed configuration (no `AdapterConfig` model, no stored import path, no JSON settings column — the whitelist is in-memory); a real RBAC extension (no new permission, no new group, no admin change); or an audit-log target (the demo does not write `AuditLog` entries). If you find yourself adding any of the above, stop: that is **V2 Option B** scope, not Option A, and requires its own proposal.

## Roadmap

A real adapter is **future work** and not part of this PR. When it lands, it will inherit from `ResourceAdapter`, be `@register`-decorated, be selected explicitly via `--adapter <dotted.path>`, and be reviewed in its own SDD cycle with its own scope, tests, and acceptance criteria.
