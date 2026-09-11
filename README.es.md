<div align="center">

# 🔐 AccessLedger

**Sistema interno de control de accesos desarrollado con Django — gestiona, audita y gobierna los permisos sobre los recursos de una organización.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![Render](https://img.shields.io/badge/Deployed-Render-46E3B7?logo=render&logoColor=white)

🌐 [Live Demo](https://web-production-0ea6.up.railway.app)

[🇬🇧 English version](README.md)

[Funcionalidades](#-funcionalidades) · [Arquitectura](#-arquitectura) · [Inicio rápido](#-inicio-rápido) · [Seguridad](#-seguridad) · [Modelo de datos](#-modelo-de-datos) · [Despliegue](#-despliegue) · [Hoja de ruta](#-hoja-de-ruta)

</div>

---

## 📋 Índice

- [El problema](#-el-problema)
- [Funcionalidades](#-funcionalidades)
- [Stack tecnológico](#-stack-tecnológico)
- [Arquitectura](#-arquitectura)
- [Modelo de datos](#-modelo-de-datos)
- [Inicio rápido](#-inicio-rápido)
- [Variables de entorno](#-variables-de-entorno)
- [Comandos de gestión](#-comandos-de-gestión)
- [Seguridad](#-seguridad)
- [Interfaz de usuario](#-interfaz-de-usuario)
- [Tests](#-tests)
- [Despliegue](#-despliegue)
- [Hoja de ruta](#-hoja-de-ruta)

---

## 🎯 El problema

En organizaciones que carecen de un sistema centralizado de gestión de accesos, los permisos se controlan mediante hojas de cálculo, hilos de correo electrónico y memoria institucional. Esto genera:

- **Accesos fantasma** — empleados o colaboradores que conservan permisos a sistemas críticos tras abandonar la organización
- **Cero auditabilidad** — ausencia de registro sobre quién concedió un acceso, cuándo y con qué justificación
- **Riesgo de cumplimiento** — imposibilidad de demostrar controles de acceso ante auditorías
- **Caos operativo** — los procesos de alta y baja requieren contactar manualmente a múltiples responsables de sistemas

**AccessLedger** resuelve este problema proporcionando una fuente única de verdad para todos los accesos a recursos de la organización, con trazabilidad completa, expiración automática y control basado en roles.

---

## ✨ Funcionalidades

| Funcionalidad                      | Descripción                                                                                                     |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **RBAC**                           | Sistema de roles en tres niveles (`viewer`, `editor`, `admin`) con permisos granulares de Django                |
| **Gestión de recursos**            | CRUD completo para servidores, bases de datos, repositorios, herramientas SaaS, dashboards y VPNs               |
| **Access Grants**                  | Asignación de niveles de acceso (`read` / `write` / `admin`) con fechas de inicio/fin y seguimiento de estado   |
| **Expiración automática**          | Comando de gestión que marca automáticamente como expirados los grants que superan su fecha de finalización     |
| **Gestión de usuarios**            | Crear, editar, activar/desactivar usuarios con asignación de roles                                              |
| **Cambio de contraseña forzado**   | Los nuevos usuarios deben cambiar su contraseña en el primer inicio de sesión mediante middleware personalizado |
| **Protección contra fuerza bruta** | `django-axes` bloquea la cuenta tras 5 intentos fallidos de inicio de sesión (1 hora de espera)                 |
| **Audit Log completo**             | Cada acción se registra con diffs de estado anterior/posterior (JSON), filtrable por acción y usuario           |
| **UI con tema oscuro**             | CSS personalizado con animaciones, modales nativos HTML5 `<dialog>`, diseño completamente responsive            |
| **Operaciones AJAX**               | Crear/editar/eliminar mediante Fetch API con respuestas JSON — sin recargas de página                           |
| **Dockerizado**                    | Un solo `docker compose up` levanta Django + PostgreSQL, listo para usar                                        |

---

## 🛠 Stack tecnológico

| Capa                | Tecnología                                                                               |
| ------------------- | ---------------------------------------------------------------------------------------- |
| **Backend**         | Python 3.12 · Django 5.2                                                                 |
| **Base de datos**   | PostgreSQL 16                                                                            |
| **Infraestructura** | Docker · Docker Compose                                                                  |
| **Frontend**        | HTML5 (`<dialog>` nativo) · CSS personalizado (tema oscuro) · Vanilla JavaScript         |
| **Seguridad**       | django-axes · Protección CSRF · `@permission_required` · `@admin_required` personalizado |
| **Driver de BD**    | psycopg 3 (adaptador PostgreSQL en Python puro)                                          |
| **Configuración**   | python-dotenv                                                                            |

---

## 🏗 Arquitectura

```
accessledger/
├── accessledger/          # Configuración del proyecto Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                  # Aplicación principal
│   ├── models.py          # Resource, AccessGrant, Profile, AuditLog
│   ├── views.py           # 19 vistas (CRUD + endpoints AJAX)
│   ├── forms.py           # Formularios Django para recursos y grants
│   ├── urls.py            # Enrutamiento URL (20 endpoints)
│   ├── decorators.py      # Decorador personalizado @admin_required
│   ├── middleware.py       # ForcePasswordChangeMiddleware
│   ├── signals.py         # Creación automática de Profile al crear User
│   ├── utils.py           # Helper log_action() para auditoría
│   ├── management/
│   │   └── commands/
│   │       ├── bootstrap_roles.py   # Inicializar grupos y permisos RBAC
│   │       ├── seed_data.py         # Poblar datos de demostración
│   │       └── expire_grants.py     # Expirar grants vencidos
│   ├── static/core/       # Recursos CSS y JavaScript
│   └── templates/core/    # 10 plantillas Django
├── templates/registration/  # Plantillas de autenticación (login, cambio de contraseña)
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh          # Ejecuta migraciones + arranca el servidor
└── requirements.txt
```

### Flujo de una petición

```
Petición del cliente
     │
     ▼
┌─────────────────────┐
│   Django Middleware   │
│  ┌─────────────────┐ │
│  │  django-axes    │ │  ← Protección contra fuerza bruta
│  │  (solo login)   │ │
│  ├─────────────────┤ │
│  │ ForcePassword   │ │  ← Redirige si must_change_password
│  │ ChangeMiddleware│ │
│  └─────────────────┘ │
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  @login_required     │  ← Puerta de autenticación
│  @permission_required│  ← Verificación de permisos RBAC
│  @admin_required     │  ← Acciones exclusivas de admin
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│   Lógica de la vista │  ← Procesar petición, validar formularios
│  ┌─────────────────┐ │
│  │  log_action()   │ │  ← Escritura en AuditLog (antes/después)
│  └─────────────────┘ │
└─────────┬───────────┘
          ▼
   Respuesta HTML o JSON
```

---

## 📊 Modelo de datos

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

### Matriz de permisos RBAC

| Permiso            | Viewer | Editor | Admin |
| ------------------ | :----: | :----: | :---: |
| Ver recursos       |   ✅   |   ✅   |  ✅   |
| Ver access grants  |   ✅   |   ✅   |  ✅   |
| Crear recursos     |   ❌   |   ✅   |  ✅   |
| Editar recursos    |   ❌   |   ✅   |  ✅   |
| Eliminar recursos  |   ❌   |   ❌   |  ✅   |
| Conceder accesos   |   ❌   |   ❌   |  ✅   |
| Revocar accesos    |   ❌   |   ❌   |  ✅   |
| Gestionar usuarios |   ❌   |   ❌   |  ✅   |
| Ver audit log      |   ❌   |   ❌   |  ✅   |

---

## 🚀 Inicio rápido

### Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y [Docker Compose](https://docs.docker.com/compose/install/) instalados

### Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/Dani1lopez/accessledger.git
cd accessledger

# 2. Configurar las variables de entorno
cp .env.example .env
# Editar .env y completar las credenciales de la base de datos

# 3. Construir y arrancar los contenedores
docker compose up --build

# 4. En otra terminal — inicializar roles y crear usuario administrador
docker exec accessledger_web python manage.py bootstrap_roles
docker exec accessledger_web python manage.py ensure_superuser

# 5. (Opcional) Cargar datos de demostración
#    En producción (DEBUG=False) hay que definir SEED_DEMO=true en el
#    entorno para habilitarlo; el comando rechaza ejecutarse de otra
#    forma y genera contraseñas aleatorias de 20 caracteres impresas
#    en stdout.
docker exec accessledger_web python manage.py seed_data

# 6. Abrir el navegador
open http://localhost:8000
```

> [!NOTE]
> Las migraciones de base de datos se ejecutan automáticamente al iniciar el contenedor mediante `entrypoint.sh` — no es necesario ejecutar `migrate` manualmente.

---

## 🔑 Variables de entorno

Crear un archivo `.env` a partir del ejemplo proporcionado:

```bash
cp .env.example .env
```

| Variable            | Descripción                           | Valor por defecto |
| ------------------- | ------------------------------------- | ----------------- |
| `POSTGRES_DB`       | Nombre de la base de datos PostgreSQL | _(obligatorio)_   |
| `POSTGRES_USER`     | Usuario de PostgreSQL                 | _(obligatorio)_   |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL              | _(obligatorio)_   |
| `POSTGRES_HOST`     | Host de la base de datos              | `db`              |
| `POSTGRES_PORT`     | Puerto de la base de datos            | `5432`            |
| `SECRET_KEY`        | Clave secreta de Django               | _(obligatorio)_   |
| `DEBUG`             | Activar modo depuración               | `False`           |
| `ALLOWED_HOSTS`     | Hosts permitidos separados por comas  | _(obligatorio)_   |

> [!CAUTION]
> Nunca incluya el archivo `.env` en el control de versiones. El `.gitignore` ya está configurado para excluirlo.

### Entorno de tests

Los tests pueden usar un archivo `.env.test` separado para que la configuración de la aplicación y la configuración de pruebas no se pisen entre sí. Esto es especialmente útil al ejecutar tests dentro de Docker, donde el host de la base de datos es `db` y el puerto interno de PostgreSQL es `5432`.

Crear `.env.test` localmente:

```env
POSTGRES_DB=accessledger
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

> [!NOTE]
> `POSTGRES_HOST_PORT` solo sirve para conectarse desde la máquina host hacia Docker, por ejemplo `localhost:5434`. Los contenedores deben conectarse a PostgreSQL mediante `db:5432`.

---

## ☁️ Base de datos en producción (Render + Neon)

> [!CAUTION]
> **La PostgreSQL gratuita de Render expira a los ~30 días y se elimina automáticamente.** Cuando ocurre, el deploy falla en `migrate` con:
> `django.db.utils.OperationalError: failed to resolve host 'dpg-...' : Name or service not known`
> — la `DATABASE_URL` antigua sigue apuntando a la base de datos eliminada. Hay que recrear la base de datos, actualizar la variable de entorno y redesplegar.

Para evitar que el incidente se repita cada mes, usar el **plan gratuito de Neon** (permanente, no es una prueba):

- **Región**: AWS Europa (Fráncfort) — `eu-central-1`, la misma región que el servicio web de Render.
- **Límites gratuitos**: 0.5 GB de almacenamiento, 100 CU-horas/mes, 5 GB de salida. El compute se suspende tras ~5 minutos de inactividad y se activa con la siguiente petición (unos segundos de arranque en frío en la primera llamada).
- **Cadena de conexión** (desde el dashboard de Neon):

```env
DATABASE_URL=postgres://usuario:password@ep-<proyecto>-<rama>.eu-central-1.aws.neon.tech/accessledger?sslmode=require
```

- El proyecto ya fuerza `sslmode=require` y un timeout de conexión de 10 segundos en `accessledger/settings.py`, así que la URL anterior funciona sin cambios.
- Definir `DATABASE_URL` en el servicio de Render y **eliminar cualquier `POSTGRES_HOST` / `POSTGRES_*` manual** para que solo exista una fuente de verdad.

---

## ⚙️ Comandos de gestión

| Comando           | Descripción                                                                                                                                                         |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bootstrap_roles` | Crea los tres grupos RBAC (`viewer`, `editor`, `admin`) y asigna los permisos Django correspondientes a cada uno. Idempotente — seguro de ejecutar múltiples veces. |
| `seed_data`       | Puebla la base de datos con recursos y usuarios de ejemplo para desarrollo y demostración.                                                                          |
| `expire_grants`   | Recorre todos los grants activos y marca como `expired` aquellos cuya fecha `end_at` haya sido superada. Diseñado para ejecutarse como tarea programada (cron).     |

**Ejemplo — programar la expiración automática (cron):**

```bash
# Ejecutar diariamente a medianoche
0 0 * * * docker exec accessledger_web python manage.py expire_grants
```

---

## 🛡 Seguridad

La seguridad es una prioridad de primer nivel en AccessLedger. Se han implementado las siguientes medidas:

### Autenticación y control de acceso

- **Protección contra fuerza bruta** — `django-axes` monitoriza los intentos de inicio de sesión; tras **5 intentos fallidos**, la cuenta se bloquea durante **1 hora**
- **Cambio de contraseña forzado** — el middleware personalizado `ForcePasswordChangeMiddleware` redirige a los nuevos usuarios para que cambien su contraseña inicial antes de acceder a cualquier recurso
- **Acceso basado en roles** — el decorador `@permission_required` de Django controla los permisos por grupo; un decorador personalizado `@admin_required` protege las vistas exclusivas de administración
- **Seguridad de sesión** — framework de sesiones integrado de Django con configuración segura por defecto

### Integridad de datos

- **Protección CSRF** — todos los formularios y peticiones AJAX incluyen tokens CSRF
- **Prevención de inyección SQL** — uso exclusivo del ORM de Django (sin SQL en crudo)
- **Trazabilidad completa** — el modelo `AuditLog` registra cada acción que modifica el estado, con snapshots JSON del objeto antes y después del cambio
- **Integridad referencial** — restricciones a nivel de base de datos con políticas `on_delete` apropiadas (`CASCADE`, `SET_NULL`)

### Infraestructura

- **Aislamiento del entorno** — configuración sensible cargada desde `.env` (excluido del control de versiones)
- **Imagen Docker mínima** — base `python:3.12-slim`, sin paquetes innecesarios
- **Health checks de servicio** — Docker Compose espera a que PostgreSQL esté disponible antes de arrancar Django
- **HTTPS forzado** — `SECURE_SSL_REDIRECT` redirige todo el tráfico a HTTPS
- **HSTS habilitado** — cabecera HTTP Strict Transport Security configurada para 1 año
- **Cookies seguras** — `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE` activados en producción

---

## 🖥 Interfaz de usuario

AccessLedger cuenta con una interfaz de usuario con **tema oscuro** personalizada, construida íntegramente con tecnologías web nativas — sin frameworks CSS ni librerías JavaScript.

### Pantallas principales

| Pantalla                | Descripción                                                                                                    |
| ----------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Listado de recursos** | Tabla con búsqueda de todos los recursos gestionados, con badges de tipo y etiquetas de entorno                |
| **Detalle de recurso**  | Información completa del recurso con grants asociados, creación y revocación inline de grants                  |
| **Gestión de usuarios** | Crear, editar, activar/desactivar usuarios — solo administradores                                              |
| **Audit Log**           | Registro cronológico de todas las acciones, filtrable por tipo de acción y usuario, con diffs JSON expandibles |
| **Perfil de usuario**   | Visualización de grants personales e información de la cuenta                                                  |

### Aspectos destacados del diseño

- 🌙 **Tema oscuro** con ratios de contraste cuidadosamente seleccionados
- 💫 **Animaciones CSS** para transiciones, modales y retroalimentación interactiva
- 📱 **Diseño responsive** funcional en escritorio y dispositivos móviles
- 🪟 **`<dialog>` nativo de HTML5** para modales — sin necesidad de librerías JavaScript
- ⚡ **CRUD mediante AJAX** — crear, editar y eliminar recursos sin recargas de página

---

## 🧪 Tests

El proyecto incluye una suite de tests con pytest-django que cubre casos borde de formularios (nombres duplicados, rangos de fechas inválidos), los métodos `__str__` de los modelos, la creación automática de `Profile` mediante señales de Django, y que cada rol (`viewer`, `editor`, `admin`) solo puede acceder a las vistas que sus permisos permiten. La suite se ejecuta con un único comando — consultá la invocación canónica más abajo; el conteo por archivo no se congela deliberadamente en este README.

### Recomendado: ejecutar tests dentro de Docker

Docker Compose permite que el proceso de tests acceda al servicio PostgreSQL como `db:5432`, coincidiendo con el ejemplo de `.env.test` anterior:

```bash
docker compose run --rm web pytest -v
```

Ejecutar solo los tests de creación de usuarios:

```bash
docker compose run --rm web pytest tests/test_views.py -k "UserCreate"
```

### Alternativa con Python local

Si ejecutás pytest directamente desde tu máquina host, recordá que `db` es un hostname exclusivo de Docker. Sobrescribí el host y el puerto de la base de datos para tu entorno local:

```bash
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5434 pytest -v
```

---

## 🚀 Despliegue

| Elemento | Detalle |
| -------- | ------- |
| **Plataforma** | Render |
| **Auto-deploy** | En cada push a `main` |
| **Base de datos** | PostgreSQL gestionado por Render |
| **Archivos estáticos** | Servidos por WhiteNoise |
| **Servidor WSGI** | Gunicorn |
| **Arranque** | Migraciones y `collectstatic` se ejecutan automáticamente al iniciar el contenedor mediante `entrypoint.sh` |

---

## 🗺 Hoja de ruta

> **Fundamentos V2 (esqueleto).** Existe un contrato de adaptadores V2
> bajo `core/adapters/` para describir — y eventualmente integrar con —
> servicios externos. El esqueleto es **no-op**: no hay integración
> real con proveedores, no hay ejecución programada, y no hay I/O de
> producción. Los adaptadores reales son ciclos SDD futuros; consulta
> `docs/adapters.md` para ver el contrato y los no-objetivos explícitos.

- [ ] Registro de cambios de contraseña en el audit log
- [ ] API REST con Django REST Framework
- [x] Suite de tests automatizados (pytest-django)
- [ ] Pipeline CI/CD con GitHub Actions
- [ ] Notificaciones por email para grants próximos a expirar
- [ ] Autenticación de dos factores (2FA)
- [ ] Exportación del audit log (CSV / PDF)
- [x] Despliegue en producción en Render

---

<div align="center">

**Desarrollado con** 🐍 **Python** · 🎸 **Django** · 🐘 **PostgreSQL** · 🐳 **Docker**

</div>
