#!/bin/sh
set -ex
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear
echo "Aplicando migraciones..."
python manage.py migrate --noinput
echo "Demo roles/data se crean en background (no bloquea el arranque)..."
(
  if [ -z "$DATABASE_URL" ] || [ "$SEED_DEMO" = "True" ]; then
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
