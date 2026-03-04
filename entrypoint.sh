#!/bin/sh
set -ex
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear
echo "Aplicando migraciones..."
python manage.py migrate --noinput
echo "Arrancando servidor..."
if [ "$DEBUG" = "True" ]; then
    exec python manage.py runserver 0.0.0.0:8000
else
    exec gunicorn accessledger.wsgi --bind 0.0.0.0:${PORT:-8080} --log-file -
fi