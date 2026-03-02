#!/bin/sh

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Aplicando migraciones..."
python manage.py migrate --noinput

echo "Arrancando servidor..."
exec gunicorn accessledger.wsgi --bind 0.0.0.0:8080 --log-file -
