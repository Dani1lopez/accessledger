# AccessLedger — Remediation Roadmap

**Type:** Documentation-only artifact. This document plans remediation; it makes no code, test, configuration, or infrastructure changes.
**Date:** 2026-09-13
**Evidence base (current consolidated audit, not the stale 2026-08-31 static findings):**

- Full pytest run completed after Docker/Postgres became available: **`326 passed, 1 warning`** (326 tests collected and verified in the working tree).
- `manage.py check --deploy` completed: residual warnings **security.W008** (`SECURE_SSL_REDIRECT` not enabled) and **security.W021** (`SECURE_HSTS_PRELOAD` not set). Both verified against the repository-pinned Django 5.2.15 check definitions (`requirements.txt`).
- Judgment Day double-blind review ledger: `.atl/judgment-day/ledger-round1.json` (3 confirmed CRITICAL — all fixed via #102; 23 info findings — several now confirmed defects below).
- On-disk verification pass (this session): every defect row below was re-checked against current code before being scheduled. Stale findings from `docs/audit-2026-08-31.md` that main already fixed are explicitly discarded (§4).
- Issue-tracker facts: see §2. The Issue Form is published on main (commit `25c8004`) and milestone **`Audit Remediation 2026`** is open as milestone #1. Every issue number in this document is a confirmed published mapping; no mappings are invented.

**Language note:** technical artifact in English, per project convention.

---

## 1. Current Product State

AccessLedger is a Django 5.2 single-app monolith (`core`) managing access grants to technology resources, with group RBAC (viewer/editor/admin + 2 custom permissions), forced first-login password change, HTMX + vanilla-JS UI, WhiteNoise, Gunicorn/Railway deployment.

The large remediation wave is **done and verified**: the 2026-08-31 audit change (REQ-AR-001…012, 61 scenarios, all covered by tests per `openspec/changes/audit-2026-08-31/verify-report.md`) and the Judgment Day critical findings (JD-01/02/03, fixed in #102) are closed, with `326 passed, 1 warning` on the completed full run.

What remains is a **second, smaller wave of confirmed defects** found by the current consolidated audit (§3), plus product capability gaps (§5) and hygiene (§6). The outcome of executing this roadmap is:

- **P1:** all confirmed correctness/security defects in §3 fixed with focused tests; suite green.
- **P2:** authorization policy single-sourced, grant invariants enforced, HTTPS/config docs aligned, residual ledger warnings triaged, product features delivered.

**Verified tracker-hygiene facts (working tree):** `graphify-out/` is untracked/stale tool output (gitignore it; do not commit); `gunicorn.ctl` is a live Unix domain socket (`srwxr-xr-x`) — gitignore the path, never delete it as "debris".

---

## 2. Issue-Tracker Status (as of this audit)

| Status | Issues | Action |
|---|---|---|
| **Closed** (with evidence comments) | #56, #57, #58, #59, #81 | Done — verified as closed; no further work. These covered stale findings that current main has fixed (see §4). |
| **Updated and scoped** | #62, #65, #79, #90, #98 | Scoped in this roadmap; each maps into a §3 cluster or P2 work. Do not reopen; execute residual scope from §3/P2. |
| **Open, confirmed valid** | #82 | Still valid: `entrypoint.sh:2` runs `set -ex`; the credential-bearing test at `entrypoint.sh:61` (`[ -n "$DJANGO_SUPERUSER_PASSWORD" ]`) expands the real password into the shell trace. See V-01. |
| **Published tracking** | Form published on main in commit `25c8004`; milestone `Audit Remediation 2026` open as milestone #1 | **New confirmed issues:** V-05 #105, V-06 #106, V-07 #107, V-08/V-09 #108, V-10 #109, V-11 #110, V-12 #111, V-15 #112. **Product issues:** F1 #113, F2 #114, F3 #115, F4 #116, F5 #117, F6 #118, F7 #119. **Existing equivalents reused (no duplicates created):** V-02 #72, V-03 #80, V-04 residual overlaps #78/#80, V-13 #92, V-14 #76, V-16 #84, V-17 #83; V-18 is split across existing #63/#64/#65/#97 and product #117; grant invariants cluster maps to existing #77 (duplicate active grants) and #78 (invalid grant state transitions). **#82 remains V-01.** All work items are mapped. Milestone `Audit Remediation 2026` contains **31 open issues**: existing #62, #63, #64, #65, #72, #76, #77, #78, #80, #82, #83, #84, #90, #92, #97, #98 plus new #105–#119. |

---

## 3. Confirmed Defects (current audit — P0/P1 scope)

Every row was verified in the current working tree. IDs `JD-I*` reference `.atl/judgment-day/ledger-round1.json`.

### V-01 — `set -x` conditional secret trace (issue #82, open)

- **Evidence:** `entrypoint.sh:2` (`set -ex`) + `entrypoint.sh:61` (`[ -n "$DJANGO_SUPERUSER_PASSWORD" ]`). Under `set -x`, the shell traces the test with the variable **expanded**, printing the superuser password to container logs.
- **Fix:** stop tracing credential-bearing expansions (e.g., precompute a boolean/length flag outside `set -x` visibility, or scope tracing around the block).
- **Acceptance:** traced output contains no password value for any env combination; regression test asserts the trace is credential-free.
- **Verification:** shell-behavior test (`sh -c` convention in `tests/test_infra.py`) + manual trace inspection.

### V-02 — Non-superuser admin can change superuser credentials

- **Evidence:** `core/views.py` `user_update` has no superuser-target guard — a plain `admin`-group admin can target a superuser's pk and rotate their password or strip their groups. Contrast: `user_toggle_active` protects superusers (last-superuser guard).
- **Fix:** in `user_update` (and `user_data` if sensitive), reject mutation of `is_superuser` targets by non-superuser actors, or require explicit policy per the centralized authorization module (§7).
- **Acceptance:** admin (non-superuser) POST against a superuser is rejected with a clear error; superuser actor unaffected; tests cover allow/deny matrix.
- **issue:** #72.

### V-03 — Mutation/AuditLog non-atomic sites

- **Evidence:** `_audit` context manager exists (`core/views.py:51-75`) but is dead in production (JD-I6); `resource_create`, `resource_update`, `grant_create`, and `resource_delete` still call `save()`/`delete()` + `log_action()` outside any atomic block, so a failure between mutation and audit (or the JD-01-class `DataError` pattern) can persist the mutation without the audit row. (`grant_revoke`, `user_update`, `user_toggle_active`, and the password-change view are already atomic.)
- **Fix:** route the four non-atomic sites through `_audit` (or `transaction.atomic()`), or delete `_audit` if a different single mechanism is chosen — one decision, applied everywhere.
- **Acceptance:** injected failure between save and audit leaves neither mutation nor audit row; all four sites verified by failure-injection tests.
- **issue:** #80.

### V-04 — `expire_grants` re-filter race + non-atomic audit

- **Evidence:** `core/management/commands/expire_grants.py:16-36`: PKs are snapshotted, statuses bulk-flipped, then the audit loop re-filters by `pk__in=affected_pks` **without re-checking `status="active"`** — a grant concurrently revoked between snapshot and re-filter gets an audit row falsely claiming `active → expired`. The audit loop is also outside any transaction, so a mid-loop failure leaves statuses flipped with partial audit.
- **Fix:** re-filter the audit loop with the same predicate (or lock rows / do the flip + audit in one transaction per grant).
- **Acceptance:** concurrent-revocation scenario produces no lying `GRANT_EXPIRED` row; failure mid-loop leaves state + audit consistent; postgres-marked test covers the race window.
- **issue:** residual scope overlaps existing #78/#80 — no new issue (avoid duplicates).

### V-05 — Last-superuser TOCTOU

- **Evidence:** `core/views.py` `user_toggle_active`: the last-active-superuser guard runs **before** the atomic block and is not revalidated under `select_for_update` — two concurrent toggles can both pass the guard and deactivate the last superuser (JD-I1).
- **Fix:** re-check the guard inside the atomic block on the locked row.
- **Acceptance:** concurrency test (postgres-marked) proves only one of two racing toggles succeeds; suite green.
- **issue:** #105.

### V-06 — Non-AJAX invalid POST returns `None` → 500

- **Evidence:** `user_create` (`core/views.py:404-439`) and `user_update` (`core/views.py:457-501`): when the form is invalid and the request is **not** AJAX, neither the `JsonResponse` nor the redirect branch runs and execution falls off the end → implicit `None` → 500. (Resource/grant views re-render their template instead — the asymmetry is the bug.)
- **Fix:** add the non-AJAX fall-through (re-render/redirect with form errors) for both views.
- **Acceptance:** non-AJAX invalid POST returns a rendered form with errors (or explicit 4xx), never 500; tests for both views, AJAX and non-AJAX.
- **issue:** #106.

### V-07 — Admin/superuser policy divergence (centralize here)

- **Evidence:** `admin_required` (`core/decorators.py`) checks group `"admin"` only — **no superuser bypass** — while `user_can_modify_resource` (`core/permissions/helpers.py`) grants superusers. A superuser without the admin group is denied the user-management views; nav links are gated on `perms.core.delete_resource` (`base.html:11,50,58`), a third, semantically different predicate (JD-I9, JD-I10).
- **Fix:** one authorization policy module (§7) defining `is_admin(user)` (superuser OR admin group), consumed by `admin_required`, templates, and future object-level checks.
- **Acceptance:** superuser reaches all admin views; permission matrix tests (viewer/editor/admin/superuser × admin views) green; nav visibility matches enforcement.
- **issue:** #107.

### V-08/V-09 — Forced-password middleware: logout lockout and `/admin` bypass

- **Evidence:** `core/middleware.py`: `ALLOWED_EXACT = {"/login/", "/admin/logout/"}` — a user with `must_change_password=True` **cannot log out of the main app** (`/logout/` redirects to password change forever). Simultaneously `ALLOWED_PREFIX = ("/password/", "/admin/")` lets the same forced user **browse the entire Django admin** without changing their password (bypass; tests pin both behaviors, e.g. `test_admin_subpath_not_blocked_when_forced`). Related, same file: no `/static/` exemption breaks the change-password page styling (JD-I20).
- **Fix:** allow `/logout/` exactly; narrow the admin prefix to auth/admin-auth paths; exempt static/media; add the "at least reachable exit" invariant.
- **Acceptance:** forced user can always log out and always reaches the password-change page; forced user cannot reach admin content pages; middleware tests updated in both directions.
- **issue:** #108 (includes JD-I20).

### V-10 — Activation guard bug (re-activating the last superuser is rejected)

- **Evidence:** `core/views.py` `user_toggle_active`: the last-superuser guard fires regardless of toggle **direction** — deactivating the last active superuser is correctly rejected, but re-activating an inactive last superuser is also rejected, leaving the account permanently unmanagable via the UI.
- **Fix:** only apply the last-superuser guard when the toggle would deactivate.
- **Acceptance:** reactivating the sole inactive superuser succeeds; deactivating the sole active one still 400s; both directions tested.
- **issue:** #109.

### V-11 — `grant_revoke` missing 404

- **Evidence:** `core/views.py:267`: `AccessGrant.objects.select_for_update().get(pk=pk)` raises `DoesNotExist` → 500 for a bad/unknown pk (every other view uses `get_object_or_404`).
- **Fix:** `get_object_or_404` inside the transaction (or catch and 404).
- **Acceptance:** unknown pk → 404; existing pk behavior unchanged; test added.
- **issue:** #110.

### V-12 — Stale modal role

- **Evidence:** `core/static/core/js/delegated.js` `onEditUser` (~line 316): `if (roleSel && data.group) roleSel.value = data.group;` — when the target user has **no group** (`data.group` is null), the select keeps the previously displayed role, so the edit modal shows (and would submit) a stale role.
- **Fix:** always assign the select (`data.group || ""`) and reset the form per open.
- **Acceptance:** opening the edit modal for a groupless user shows an empty role; regression test or deterministic JS checklist (no JS test runner in repo).
- **issue:** #111.

### V-13 — Repr-as-JSON snapshot parsing

- **Evidence:** `AuditLog.before/after` are `JSONField` (`core/models.py:93-94`), but `_audit_log.html:49-50` renders them into `data-*` attributes, where Django stringifies dicts as **Python repr** (single quotes, `True`/`False`/`None`); `delegated.js:68-75` `parseSnapshot` then blind-replaces `'`→`"`, `True`/`False`→`true`/`false`, `None`→`null` to force JSON.parse (JD-I8). Any apostrophe inside a note/username string corrupts the payload → broken/empty diff modal.
- **Fix:** serialize snapshots server-side to real JSON (`json.dumps` via a template filter or precomputed field) and parse client-side without blind replaces.
- **Acceptance:** diff modal renders correctly for values containing apostrophes, booleans, and `None`; template+JS covered by deterministic checklist until a JS runner exists.
- **issue:** #92.

### V-14 — Admin password-validation bypass

- **Evidence:** `AUTH_PASSWORD_VALIDATORS` is configured (`settings.py:137+`) but `core/forms.py` (`UserForm` password field line ~31, `UserCreateForm` line ~39) never calls `validate_password` — admins can create/update users with weak passwords that Django's own auth views would reject (JD-I3).
- **Fix:** run `django.contrib.auth.password_validation.validate_password` in both forms' clean methods.
- **Acceptance:** weak password rejected with field errors in both flows; strong password accepted; tests mirror the built-in validator behavior.
- **issue:** #76.

### V-15 — Conditional inline-handler XSS

- **Evidence:** `core/templates/core/resource_detail.html:135`: `onsubmit="return confirm('¿Revocar acceso de @{{ g.user.username }}?')"` interpolates user content into an inline JS handler. Safe **today** only because Django's username validator excludes quotes — the same latent class PR #100 closed for the `USERNAME` global (REQ-AR-012 Scenario 12.6). Inline handlers are also incompatible with any future CSP.
- **Fix:** move the confirm to the delegated submit handler (data-attribute + `textContent`) or server-side validation.
- **Acceptance:** no user content inside inline handlers; behavior identical in UI; checklist + grep gate (`grep -rn "on[a-z]*=" core/templates/ templates/` returns no user-content interpolations).
- **issue:** #112.

### V-16 — HTTPS docs/config mismatch (includes deploy-check W008)

- **Evidence:** README badge says "Deployed Render" while the live demo is a Railway URL (`README.md:11,13`); `CSRF_TRUSTED_ORIGINS` default is `https://*.onrender.com` (`settings.py:129-133`); `SECURE_SSL_REDIRECT` is not enabled (deploy-check **W008**), and `SECURE_HSTS_PRELOAD` is unset (**W021**).
- **Fix:** align docs and defaults on Railway (`*.up.railway.app`), enable `SECURE_SSL_REDIRECT`/`SECURE_HSTS_PRELOAD` behind `not DEBUG` (or document why the proxy handles it), and make `CSRF_TRUSTED_ORIGINS` mandatory per environment.
- **Acceptance:** `check --deploy` on production settings emits no W008/W021 (or each has a documented, reviewed reason); README and settings reference one platform; grep for `onrender` returns zero production references.
- **issue:** #84.

### V-17 — Background seed race

- **Evidence:** `entrypoint.sh:54-57`: `bootstrap_roles && seed_data` runs in an un-awaited background subshell with failures swallowed by `|| echo WARNING`; Gunicorn starts concurrently, so early requests can hit an unseeded permission state, and seed failure is invisible beyond one log line.
- **Fix:** await/verify seeding before `exec gunicorn` (or make failure loud and blocking per env), keeping dev convenience.
- **Acceptance:** deployed boot never serves before seeding completed or explicitly failed-loud; `tests/test_infra.py` shell-behavior tests cover ordering and failure propagation.
- **issue:** #83.

### V-18 — Unbounded / N+1 endpoints and connection/worker risks

- **Evidence:** `user_list` (`core/views.py:281-286`) returns **all users** with no pagination; `resource_detail` renders a resource's full grant list unpaginated; snapshot helpers can trigger lazy owner queries (JD-I21); `DATABASES` has no `CONN_MAX_AGE` (fresh TCP connection per request); Gunicorn runs a single sync worker (`entrypoint.sh`, `Procfile`).
- **Fix (small, ordered):** paginate/bound `user_list`, paginate `resource_detail` grants, add `CONN_MAX_AGE=60`, and introduce a minimal `gunicorn.conf.py` (workers, timeout, max-requests). Caching/django-redis stays out of scope until measured need.
- **Acceptance:** each endpoint bounded under a fixture dataset; deploy checklist records worker/timeout values; no N+1 assertions (Django `assertNumQueries` or capture) on the two fixed endpoints.
- **issue:** split across existing #63/#64/#65/#97 and product #117 (F5) — no new issue (avoid duplicates).

### Grant invariants cluster (parent item: duplicate grants / invariants / transitions)

- **Evidence:** `AccessGrant.Meta` (`core/models.py`) has indexes but **no unique constraint** on `(user, resource, status='active')`-style invariant (JD-I7); `grant_create` allows grants born already-expired (`end_at <= start_at`) or targeting inactive users (JD-I18); `grant_revoke` has no status precondition and can overwrite an already-expired grant with `revoked` (JD-I5).
- **Fix:** DB-level partial unique constraint for one active grant per (user, resource); form-level validation of dates/target state; transition precondition in `grant_revoke` (409/no-op rule decided once in the policy module).
- **Acceptance:** duplicate active grant rejected at DB and form level; expired-born grant rejected; revoking an expired grant has one defined behavior with a test; migration reviewed.
- **issue:** existing #77 (duplicate active grants) and #78 (invalid grant state transitions) — no new issue (avoid duplicates).

**P1 ordering note:** V-07 (policy module) lands first — V-02 and the invariant cluster consume it. Everything else is independent.

---

## 4. Explicitly Discarded (stale — already fixed on main)

Do **not** open issues for these; if a stale tracker item resurfaces, close it citing this section. Fix evidence: `openspec/changes/audit-2026-08-31/verify-report.md` + on-disk verification this session.

| Stale claim | Why discarded |
|---|---|
| `user_create` role crash (`user.groups.first().name` unguarded) | Fixed: all role sites use `user_role(user)` helper with `groups.exists()` guard (`core/utils/snapshots.py`). Verify-report criterion 1 PASS. |
| `user_update` mutation without `transaction.atomic()` | Fixed: user_update writes inside `transaction.atomic()` (`core/views.py`, atomic block verified on disk). |
| `grant_revoke` race / no lock | Fixed: `select_for_update()` inside `transaction.atomic()` (`core/views.py:267`). Verify-report criterion 3 PASS. |
| Hardcoded seed passwords | Fixed: `get_random_string(length=20)` (`seed_data.py`); verify-report criterion 5 PASS. |
| `SECRET_KEY` missing fail-fast | Fixed: dict-access + `ImproperlyConfigured` guard (`settings.py:29-31`); verify-report criterion 4 PASS. |
| `expire_grants` never writes `GRANT_EXPIRED` | Fixed: command emits one audit row per expired grant (`expire_grants.py:27-36`); remaining race/non-atomicity is V-04, a different defect. |
| `ForcePasswordChangeMiddleware` blocks `/admin/login/` | Fixed: prefix matching covers `/admin/` family; `ALLOWED_PREFIX` verified on disk. Residual problems are the *opposite* direction (V-08/V-09). |
| `ALLOWED_HOSTS` parses empty as `[""]` | Fixed: deploy-check custom checks cover configuration (verify-report criteria 7.x). |
| `ensure_superuser` non-atomic / fail-open | Fixed: atomic + rollback + `--require-env` per commits `194545b`, `826700a` and `test_ensure_superuser_require_env.py`. Residual: V-01 (trace secret), a different defect. |
| GET-render branches on POST endpoints / self-toggle | Fixed: `@require_POST` on destructive views; self-deactivation guard REQ-AR-011 (tests green). |
| `USERNAME` global XSS coupling | Fixed: PR #100 closed REQ-AR-012 Scenario 12.6. Residual latent class is V-15. |
| `AuditLog.object_repr` overflow (JD-01), password-change ordering (JD-02), `SEED_DEMO` case mismatch (JD-03) | Fixed via #102 (`fix-judgment-day-critical`), verified in `openspec/changes/fix-judgment-day-critical/`. |
| "Missing `.dockerignore` / secret leak into image" | `.dockerignore` exists and excludes `.env`, `.env.*`, venvs, caches, `.git` — verified on disk. No secret leak. |
| `graphify-out/` stale repo debris | Untracked regenerable tool output; gitignore is sufficient hygiene, not a defect. |
| `gunicorn.ctl` stale file | Live Unix domain socket; correct action is gitignoring the path (backlog), never deletion. |

---

## 5. Product Roadmap (user-facing gaps — evidence current)

| # | Feature | Verified current gap | Scope sketch | Acceptance criteria | Issue |
|---|---|---|---|---|---|
| F1 | Server-side search & filtering | No search/filter on any list view (`resource_list`, `audit_log`, `user_management` have pagination but no query params) | Query params + server-filtered partials per HTMX pattern | Filter by name/type/environment/status works via HTMX and full reloads; empty state handled; tests green | #113 |
| F2 | My Access | `user_profile` renders account info only — no grant listing | Read-only view of the logged-in user's grants (active/expired) | All authenticated users see only their own rows; permission tests | #114 |
| F3 | Audit filtering & export | `audit_log` is paginated but unfilterable; no export | Filters (action/user/object/date range) + CSV export respecting filters; admin-gated | Filters compose; export matches filtered queryset | #115 |
| F4 | Password reset flow | No reset URLs/templates anywhere (verified by grep) | Django built-in `PasswordResetView` + templates + email backend config | End-to-end reset works; forced-user scenario no longer requires shell access | #116 |
| F5 | Grant pagination (narrowed) | `resource_list`, `user_management`, `audit_log` are **already paginated** (`_paginate`, PAGE_SIZE 20); `resource_detail`'s grant list is the remaining unbounded list | `Paginator` on the detail-page grants | Bounded queryset under fixtures; page controls consistent with `_pagination.html` | #117 |
| F6 | Health endpoint | No `/health/` route (verified); no compose healthcheck | Minimal unauthenticated 200 + DB check; wire into `docker-compose.yml` | Healthcheck passes in compose; leaks nothing | #118 |
| F7 | Expiry notifications | Grants expire silently; `expire_grants` is never scheduled (JD-I4) | Digest notifying resource owners/users within a configurable window | Depends on V-04 (correct, race-free expiry audit) | #119 |

**Dependencies:** F4 depends on V-08 (logout lockout removed first). F7 depends on V-04. F1/F3/F5 share the filter/pagination foundation; do F5 first. F2/F6 independent after P1.

---

## 6. Backlog / residual ledger items (P2, non-blocking)

| Item | Source | Action |
|---|---|---|
| HTMX loaded from unpkg CDN without SRI | JD-I11 | Self-host or add `integrity` attribute; tie to V-16/V-15 CSP work |
| `STATICFILES_STORAGE` deprecated (Django 5.2 → `STORAGES`) | JD-I13 | Migrate setting; no behavior change expected |
| `settings_test` hardcodes dev-personal DB defaults | JD-I14 | Neutralize test-settings DB defaults; keep SQLite CI default |
| `expire_grants` automation absent (no cron/celery/compose schedule) | JD-I4 | Schedule via platform job or compose service; prerequisite for F7 |
| Admin password rotation logged only as generic `USER_UPDATED` | JD-I19 | Distinct action or enriched after-snapshot |
| Snapshot docstring "No DB queries" false (lazy owner query) | JD-I21 | Fix docstring or prefetch; feeds V-18 N+1 work |
| Unused import (`axes` admin) in `test_views.py`; unreachable GET branches after `@require_POST` (V-23-class) | JD-I16, JD-I23 | Cleanup batch |
| `gitignore` `graphify-out/` and `gunicorn.ctl` (keep socket) | working tree | Hygiene PR, no behavior change |

---

## 7. Architecture Direction (unchanged — evidence remains current)

**Recommended: small domain methods + centralized authorization policy.**

- **Small domain methods** stay right-sized: the audit change already extracted `resource_snapshot` / `grant_snapshot` / `user_role` (`core/utils/snapshots.py`) and `_ensure_must_change_profile`; the remaining duplication is behavioral (V-03 atomicity decision, V-04 expiry audit, grant invariants), which belongs in model/manager-level methods, not a new layer.
- **Centralized authorization policy** is now *more* justified, not less: V-07 shows three divergent predicates (group-only `admin_required`, superuser-aware `user_can_modify_resource`, template-level `perms.core.delete_resource`), and V-02 shows the missing superuser-target rule. One policy module consumed by decorators, views, and templates is the minimal fix; object-level rules then attach to the same module.

**Rejected alternatives (verdicts stand):**

| Proposal | Verdict | Reason |
|---|---|---|
| Repository layer | Reject | Django ORM is the repository; duplication is behavioral, not query-construction. |
| CQRS | Reject | Read/write paths are not divergent; HTMX partial/full duality already shares templates. |
| Event sourcing | Reject | `AuditLog` already provides the immutable event record; replay is not a requirement. |
| DI framework | Reject | Would fight Django; import graph is clean and acyclic (audit-verified). |
| Large service layer | Reject for now | Revisit only if business logic outgrows views after §5 lands. |

---

## 8. Phases

Dependency order: **P0 gates P1** (policy decision + tracker alignment) → **P1** fixes confirmed defects → **P2** hardening/backlog → product track (§5) after P1.

### P0 — Scoping & tracker (no product code)

| Step | Action | Acceptance criterion | State |
|---|---|---|---|
| 0.1 | Publish the YAML Issue Forms the publication policy requires | Forms reach the default branch; issue creation unblocked | **Done** — published on main in commit `25c8004` |
| 0.2 | Create issues for V-01…V-18 and the §5 features | Every roadmap row has an issue; no invented numbers | **Done** — new issues #105–#112 and #113–#119 filed; existing equivalents reused (#72, #76, #77, #78, #80, #83, #84, #92, #63, #64, #65, #97, #82); milestone `Audit Remediation 2026` (#1) holds 31 open issues (existing #62/#63/#64/#65/#72/#76/#77/#78/#80/#82/#83/#84/#90/#92/#97/#98 + #105–#119) |
| 0.3 | Decide the V-03 mechanism (adopt `_audit` everywhere vs delete it) | One decision recorded, applied to all four sites | Open |
| 0.4 | Decide the revoke-transition rule (precondition + status code) for the invariants cluster | Documented in the policy module | Open |

**Exit gate:** tracker matches this document; no code changed in P0.

### P1 — Confirmed defect fixes (small PRs, one cluster each)

| Order | Cluster | Items | Verification |
|---|---|---|---|
| 1.1 | Authorization policy | V-07, then V-02 | Permission-matrix tests; superuser/admin/viewer × admin views |
| 1.2 | Atomicity | V-03, V-04 | Failure-injection tests; postgres-marked race test |
| 1.3 | Concurrency & guards | V-05, V-10, V-11 | postgres-marked TOCTOU test; direction-matrix toggle tests; 404 test |
| 1.4 | Forced-password flows | V-08, V-09 (+ JD-I20) | Middleware tests in both directions (logout allowed, admin content blocked) |
| 1.5 | HTTP correctness | V-06 | Non-AJAX invalid POST tests for user_create/user_update |
| 1.6 | Client correctness | V-12, V-13 | Deterministic JS checklist + template-serialization tests |
| 1.7 | Validation | V-14 | Validator behavior tests on both forms |
| 1.8 | Boot & config | V-01, V-16, V-17 | Shell-trace credential-free test; `check --deploy` clean of W008/W021 (or documented); infra tests for seed ordering |
| 1.9 | Bounds | V-18 | Bounded-queryset tests + query-count assertions |

**Exit gate:** full pytest green (`326+` tests, now including the new focused tests); every fix has a behavior-first test that would fail on pre-fix code.

### P2 — Hardening & product track

| Order | Work | Verification |
|---|---|---|
| 2.1 | Grant invariants cluster (§3) + migration review | DB/form-level rejection tests; migration reviewed |
| 2.2 | Residual ledger/backlog batch (§6) | Item-level checks; suite green |
| 2.3 | Product features F5 → F1 → F2 → F3 → F6 → F4 → F7 (§5 dependencies) | Per-feature acceptance criteria from §5 |

---

## 9. Master Checklist

- [x] **P0** Issue Form published to the default branch (commit `25c8004`); milestone `Audit Remediation 2026` open as milestone #1
- [x] **P0** Issues mapped for V-01…V-18 and F1–F7 (new #105–#112, #113–#119; existing #72/#76/#77/#78/#80/#83/#84/#92/#63/#64/#65/#97 reused; #82 remains V-01) — milestone `Audit Remediation 2026` holds 31 open issues
- [ ] **P0** V-03 mechanism and revoke-transition rule decided
- [ ] **P1** V-01…V-18 fixed, each with a behavior-first test; full suite green
- [ ] **P1** `check --deploy` free of unexplained W008/W021
- [ ] **P1** Full-run baseline updated (currently `326 passed, 1 warning`)
- [ ] **P2** Grant invariants enforced (DB + form + transition)
- [ ] **P2** Residual ledger items closed or consciously deferred with reasons
- [ ] **Track** F5 → F1 → F2 → F3 → F6 → F4 → F7 delivered per §5 acceptance criteria
- [ ] **Discard** No issues opened for §4 items; stale tracker entries stay closed
- [ ] **Ongoing** No commit/stage/push by the audit agent; review stays human-owned

---

## 10. Boundaries of This Document

- This roadmap reflects the **current consolidated audit** (ledger + verify reports + this session's on-disk verification), not the stale 2026-08-31 static findings — those are discarded in §4 with fix evidence.
- Issue numbers in this document are confirmed published mappings supplied by the tracker state: new issues #105–#112 (defects) and #113–#119 (product features); existing equivalents reused instead of duplicates (#72, #76, #77, #78, #80, #83, #84, #92, #63, #64, #65, #97, #82). Milestone `Audit Remediation 2026` (#1) contains 31 open issues: existing #62/#63/#64/#65/#72/#76/#77/#78/#80/#82/#83/#84/#90/#92/#97/#98 plus new #105–#119.
- Severity labels are the consolidated audit's; nothing here authorizes code changes — all implementation flows through the mapped issues.
