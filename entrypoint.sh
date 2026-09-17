#!/bin/sh
set -e

echo "Waiting for the database to be ready..."
python - <<'PY'
import os
import sys
import time

import psycopg

retries = int(os.environ.get("DB_READY_RETRIES", "30"))
wait = float(os.environ.get("DB_READY_WAIT", "2"))

if os.environ.get("DATABASE_URL"):
    def connect():
        return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5)
else:
    params = {
        "host": os.environ.get("POSTGRES_HOST", "db"),
        "port": os.environ.get("POSTGRES_PORT", "5432"),
        "dbname": os.environ.get("POSTGRES_DB", "postgres"),
        "user": os.environ.get("POSTGRES_USER", "postgres"),
        "password": os.environ.get("POSTGRES_PASSWORD", ""),
    }

    def connect():
        return psycopg.connect(**params, connect_timeout=5)

for attempt in range(1, retries + 1):
    try:
        conn = connect()
    except Exception as exc:
        print(f"[db-ready] attempt {attempt}/{retries} failed: {exc}", flush=True)
        if attempt < retries:
            time.sleep(wait)
    else:
        conn.close()
        print(f"[db-ready] database is ready (attempt {attempt}/{retries})", flush=True)
        sys.exit(0)

print(
    f"[db-ready] FATAL: database not reachable after {retries} attempts; "
    "refusing to start the server against a dead database.",
    flush=True,
)
sys.exit(1)
PY

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear
echo "Aplicando migraciones..."
python manage.py migrate --noinput
echo "Demo roles/data se crean en background (no bloquea el arranque)..."
(
  if [ -z "$DATABASE_URL" ] || [ "$SEED_DEMO" = "true" ]; then
    python manage.py bootstrap_roles && python manage.py seed_data || echo "WARNING: demo seeding falló — ignorando"
  fi
) &
echo "Creando superusuario si no existe..."
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py ensure_superuser
fi
echo "Arrancando servidor..."
if [ "$DEBUG" = "True" ]; then
  exec python manage.py runserver 0.0.0.0:8000
else
  exec gunicorn accessledger.wsgi --bind 0.0.0.0:${PORT:-8080} --log-file -
fi
