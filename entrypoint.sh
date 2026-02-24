#!/bin/sh

echo "Aplicando migraciones..."
python manage.py migrate --noinput

echo "Arrancado servidor..."
exec python manage.py runserver 0.0.0.0:8000