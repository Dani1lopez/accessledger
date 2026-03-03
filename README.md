<div align="center">

# 🔐 AccessLedger

**Internal access control system built with Django — manage, audit, and enforce resource permissions across your organization.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![Railway](https://img.shields.io/badge/Deployed-Railway-8B5CF6?logo=railway&logoColor=white)

🌐 [Live Demo](https://web-production-0ea6.up.railway.app)

[🇪🇸 Versión en español](README.es.md)

[Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [Security](#-security) · [Data Model](#-data-model) · [Deployment](#-deployment) · [Roadmap](#-roadmap)

</div>

---

## 📋 Table of Contents

- [The Problem](#-the-problem)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Data Model](#-data-model)
- [Quick Start](#-quick-start)
- [Environment Variables](#-environment-variables)
- [Management Commands](#-management-commands)
- [Security](#-security)
- [UI Overview](#-ui-overview)
- [Deployment](#-deployment)
- [Roadmap](#-roadmap)

---

## 🎯 The Problem

In organizations without a centralized access management system, permissions are tracked through spreadsheets, email threads, and institutional memory. This leads to:

- **Shadow access** — former employees or contractors retaining permissions to critical systems
- **Zero auditability** — no record of who granted access, when, or why
- **Compliance risk** — inability to prove access controls during audits
- **Operational chaos** — onboarding/offboarding requires contacting multiple system owners manually

**AccessLedger** solves this by providing a single source of truth for all resource access across your organization — with full audit trails, automatic expiration, and role-based controls.

---

## ✨ Features

| Feature                    | Description                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------------ |
| **RBAC**                   | Three-tier role system (`viewer`, `editor`, `admin`) with granular Django permissions      |
| **Resource Management**    | Full CRUD for servers, databases, repos, SaaS tools, dashboards, and VPNs                  |
| **Access Grants**          | Assign access levels (`read` / `write` / `admin`) with start/end dates and status tracking |
| **Auto-Expiration**        | Management command automatically expires grants past their end date                        |
| **User Management**        | Create, edit, activate/deactivate users with role assignment                               |
| **Forced Password Change** | New users must change their password on first login via custom middleware                  |
| **Brute Force Protection** | `django-axes` locks accounts after 5 failed login attempts (1-hour cooldown)               |
| **Full Audit Log**         | Every action recorded with before/after state diffs (JSON), filterable by action and user  |
| **Dark Theme UI**          | Custom CSS with animations, native HTML5 `<dialog>` modals, fully responsive               |
| **AJAX Operations**        | Fetch API-driven create/edit/delete with JSON responses — no full page reloads             |
| **Dockerized**             | Single `docker compose up` spins up Django + PostgreSQL, ready to go                       |

---

## 🛠 Tech Stack

| Layer              | Technology                                                                        |
| ------------------ | --------------------------------------------------------------------------------- |
| **Backend**        | Python 3.12 · Django 5.2                                                          |
| **Database**       | PostgreSQL 16                                                                     |
| **Infrastructure** | Docker · Docker Compose                                                           |
| **Frontend**       | HTML5 (native `<dialog>`) · Custom CSS (dark theme) · Vanilla JavaScript          |
| **Security**       | django-axes · CSRF protection · `@permission_required` · custom `@admin_required` |
| **DB Driver**      | psycopg 3 (pure Python PostgreSQL adapter)                                        |
| **Config**         | python-dotenv                                                                     |

---

## 🏗 Architecture

```
accessledger/
├── accessledger/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                  # Main application
│   ├── models.py          # Resource, AccessGrant, Profile, AuditLog
│   ├── views.py           # 19 views (CRUD + AJAX endpoints)
│   ├── forms.py           # Django forms for resources and grants
│   ├── urls.py            # URL routing (20 endpoints)
│   ├── decorators.py      # @admin_required custom decorator
│   ├── middleware.py       # ForcePasswordChangeMiddleware
│   ├── signals.py         # Auto-create Profile on User creation
│   ├── utils.py           # log_action() audit helper
│   ├── management/
│   │   └── commands/
│   │       ├── bootstrap_roles.py   # Initialize RBAC groups & permissions
│   │       ├── seed_data.py         # Populate demo data
│   │       └── expire_grants.py     # Auto-expire past-due grants
│   ├── static/core/       # CSS & JavaScript assets
│   └── templates/core/    # 10 Django templates
├── templates/registration/  # Auth templates (login, password change)
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh          # Runs migrations + starts dev server
└── requirements.txt
```

### Request Flow

```
Client Request
     │
     ▼
┌─────────────────────┐
│   Django Middleware   │
│  ┌─────────────────┐ │
│  │  django-axes    │ │  ← Brute force protection
│  │  (login only)   │ │
│  ├─────────────────┤ │
│  │ ForcePassword   │ │  ← Redirect if must_change_password
│  │ ChangeMiddleware│ │
│  └─────────────────┘ │
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  @login_required     │  ← Authentication gate
│  @permission_required│  ← RBAC permission check
│  @admin_required     │  ← Admin-only actions
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│     View Logic       │  ← Process request, validate forms
│  ┌─────────────────┐ │
│  │  log_action()   │ │  ← Write to AuditLog (before/after)
│  └─────────────────┘ │
└─────────┬───────────┘
          ▼
   HTML or JSON Response
```

---

## 📊 Data Model

```
┌──────────────────────────┐       ┌──────────────────────────────┐
│        Resource           │       │        AccessGrant            │
├──────────────────────────┤       ├──────────────────────────────┤
│ id           PK           │       │ id             PK             │
│ name         VARCHAR(120)  │◄──────│ resource_id    FK → Resource  │
│ resource_type ENUM         │       │ user_id        FK → User      │
│   repo│server│vpn│saas│   │       │ access_level   ENUM           │
│   database│dashboard│other│       │   read │ write │ admin        │
│ environment  ENUM          │       │ start_at       DATETIME       │
│   prod│staging│dev│na      │       │ end_at         DATETIME       │
│ url          URL           │       │ status         ENUM           │
│ owner_id     FK → User     │       │   active │ revoked │ expired  │
│ is_active    BOOLEAN       │       │ notes          TEXT           │
│ created_at   DATETIME      │       └──────────────────────────────┘
│ updated_at   DATETIME      │
└──────────────────────────┘
                                    ┌──────────────────────────────┐
┌──────────────────────────┐       │         AuditLog              │
│        Profile            │       ├──────────────────────────────┤
├──────────────────────────┤       │ id             PK             │
│ id           PK           │       │ user_id        FK → User      │
│ user_id      FK → User    │       │ action         ENUM           │
│ must_change_password BOOL  │       │   resource_created│updated│  │
└──────────────────────────┘       │   deleted│grant_created│     │
                                    │   revoked│expired│user_*     │
                                    │ object_type    VARCHAR(20)    │
                                    │ object_id      INT            │
                                    │ object_repr    VARCHAR(80)    │
                                    │ before         JSON (nullable)│
                                    │ after          JSON (nullable)│
                                    │ timestamp      DATETIME       │
                                    └──────────────────────────────┘
```

### RBAC Permission Matrix

| Permission         | Viewer | Editor | Admin |
| ------------------ | :----: | :----: | :---: |
| View resources     |   ✅   |   ✅   |  ✅   |
| View access grants |   ✅   |   ✅   |  ✅   |
| Create resources   |   ❌   |   ✅   |  ✅   |
| Edit resources     |   ❌   |   ✅   |  ✅   |
| Delete resources   |   ❌   |   ❌   |  ✅   |
| Grant access       |   ❌   |   ❌   |  ✅   |
| Revoke access      |   ❌   |   ❌   |  ✅   |
| Manage users       |   ❌   |   ❌   |  ✅   |
| View audit log     |   ❌   |   ❌   |  ✅   |

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/) installed

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/Dani1lopez/accessledger.git
cd accessledger

# 2. Configure environment variables
cp .env.example .env
# Edit .env and fill in your database credentials

# 3. Build and start the containers
docker compose up --build

# 4. In a new terminal — bootstrap roles and create your admin user
docker exec accessledger_web python manage.py bootstrap_roles
docker exec accessledger_web python manage.py createsuperuser

# 5. (Optional) Load demo data
docker exec accessledger_web python manage.py seed_data

# 6. Open your browser
open http://localhost:8000
```

> [!NOTE]
> Database migrations run automatically on container startup via `entrypoint.sh` — no manual `migrate` step needed.

---

## 🔑 Environment Variables

Create a `.env` file from the provided example:

```bash
cp .env.example .env
```

| Variable            | Description              | Default      |
| ------------------- | ------------------------ | ------------ |
| `POSTGRES_DB`       | PostgreSQL database name | _(required)_ |
| `POSTGRES_USER`     | PostgreSQL user          | _(required)_ |
| `POSTGRES_PASSWORD` | PostgreSQL password      | _(required)_ |
| `POSTGRES_HOST`     | Database host            | `db`         |
| `POSTGRES_PORT`     | Database port            | `5432`       |
| `SECRET_KEY`        | Django secret key        | _(required)_ |
| `DEBUG`             | Enable debug mode        | `False`      |
| `ALLOWED_HOSTS`     | Comma-separated allowed hosts | _(required)_ |

> [!CAUTION]
> Never commit your `.env` file to version control. The `.gitignore` is already configured to exclude it.

---

## ⚙️ Management Commands

| Command           | Description                                                                                                                                              |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bootstrap_roles` | Creates the three RBAC groups (`viewer`, `editor`, `admin`) and assigns the correct Django permissions to each. Idempotent — safe to run multiple times. |
| `seed_data`       | Populates the database with sample resources and users for development/demo purposes.                                                                    |
| `expire_grants`   | Scans all active grants and marks those past their `end_at` date as `expired`. Designed to run as a scheduled task (cron).                               |

**Example — schedule auto-expiration (cron):**

```bash
# Run daily at midnight
0 0 * * * docker exec accessledger_web python manage.py expire_grants
```

---

## 🛡 Security

Security is a first-class concern in AccessLedger. The following measures are implemented:

### Authentication & Access Control

- **Brute force protection** — `django-axes` monitors login attempts; after **5 failed attempts**, the account is locked for **1 hour**
- **Forced password change** — custom `ForcePasswordChangeMiddleware` redirects new users to change their initial password before accessing any resource
- **Role-based access** — Django's `@permission_required` decorator enforces per-group permissions; a custom `@admin_required` decorator protects admin-only views
- **Session security** — Django's built-in session framework with secure defaults

### Data Integrity

- **CSRF protection** — all forms and AJAX requests include CSRF tokens
- **SQL injection prevention** — exclusively uses Django ORM (no raw SQL)
- **Full audit trail** — `AuditLog` model captures every state-changing action with JSON snapshots of the object's state before and after the change
- **Foreign key integrity** — database-level constraints with appropriate `on_delete` policies (`CASCADE`, `SET_NULL`)

### Infrastructure

- **Environment isolation** — sensitive configuration loaded from `.env` (excluded from version control)
- **Minimal Docker image** — `python:3.12-slim` base, no unnecessary packages
- **HTTPS enforced** — `SECURE_SSL_REDIRECT` ensures all traffic is redirected to HTTPS
- **HSTS enabled** — HTTP Strict Transport Security header set for 1 year
- **Secure cookie flags** — `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` enabled in production
- **Service health checks** — Docker Compose waits for PostgreSQL readiness before starting Django

---

## 🖥 UI Overview

AccessLedger features a custom **dark theme UI** built entirely with native web technologies — no CSS frameworks, no JavaScript libraries.

### Key Screens

| Screen              | Description                                                                                         |
| ------------------- | --------------------------------------------------------------------------------------------------- |
| **Resource List**   | Searchable table of all managed resources with type badges and environment tags                     |
| **Resource Detail** | Full resource info with associated grants, inline grant creation and revocation                     |
| **User Management** | Create, edit, activate/deactivate users — admin only                                                |
| **Audit Log**       | Chronological record of all actions, filterable by action type and user, with expandable JSON diffs |
| **User Profile**    | View personal grants and account information                                                        |

### Design Highlights

- 🌙 **Dark theme** with carefully chosen contrast ratios
- 💫 **CSS animations** for transitions, modals, and interactive feedback
- 📱 **Responsive layout** that works on desktop and mobile
- 🪟 **Native HTML5 `<dialog>`** for modals — no JavaScript modal libraries needed
- ⚡ **AJAX-driven CRUD** — create, edit, and delete resources without page reloads

---

## 🧪 Testing

The project includes a suite of 21 automated tests built with pytest-django, covering three layers:

| Layer | File | Tests |
|-------|------|-------|
| Form validation | `tests/test_forms.py` | 7 |
| Model logic & signals | `tests/test_models.py` | 4 |
| View permissions (RBAC) | `tests/test_views.py` | 10 |

Tests verify form edge cases (duplicate names, invalid date ranges), model `__str__` methods, the auto-creation of `Profile` via Django signals, and that each role (`viewer`, `editor`, `admin`) can only access the views their permissions allow.

To run the test suite locally, you need PostgreSQL running and a `accessledger/settings_test.py` configured with your local database credentials:
```bash
pytest -v
```

---

## 🚀 Deployment

| Item | Detail |
| ---- | ------ |
| **Platform** | Railway |
| **Auto-deploy** | On every push to `main` |
| **Database** | PostgreSQL managed by Railway |
| **Static files** | Served by WhiteNoise |
| **WSGI server** | Gunicorn |
| **Startup** | Migrations and `collectstatic` run automatically on container start via `entrypoint.sh` |

---

## 🗺 Roadmap

- [ ] Password change events in the audit log
- [ ] REST API with Django REST Framework
- [x] Automated test suite (pytest-django)
- [ ] CI/CD pipeline with GitHub Actions
- [ ] Email notifications for grants nearing expiration
- [ ] Two-factor authentication (2FA)
- [ ] Audit log export (CSV / PDF)
- [x] Production deployment on Railway

---

<div align="center">

**Built with** 🐍 **Python** · 🎸 **Django** · 🐘 **PostgreSQL** · 🐳 **Docker**

</div>
