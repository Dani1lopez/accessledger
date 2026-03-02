#!/bin/sh
echo "Collecting static files..."
python manage.py collectstatic --noinput 2>&1
echo "Aplicando migraciones..."
python manage.py migrate --noinput 2>&1 || { echo "MIGRATE FAILED"; exit 1; }
echo "Arrancando servidor..."
exec gunicorn accessledger.wsgi --bind 0.0.0.0:${PORT:-8080} --log-file -