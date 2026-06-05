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
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
  DJANGO_SUPERUSER_PASSWORD="$DJANGO_SUPERUSER_PASSWORD" python manage.py createsuperuser \
    --noinput \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "$DJANGO_SUPERUSER_EMAIL" 2>&1 || echo "WARNING: superuser creation skipped or failed"

  echo "Asignando grupo admin al superusuario..."
  python manage.py shell -c "
from django.contrib.auth.models import User, Group
try:
    u = User.objects.get(username='$DJANGO_SUPERUSER_USERNAME')
    g = Group.objects.get(name='admin')
    u.groups.add(g)
    u.save()
    print('Admin group assigned to $DJANGO_SUPERUSER_USERNAME')
except User.DoesNotExist:
    print('WARNING: user $DJANGO_SUPERUSER_USERNAME does not exist yet')
except Group.DoesNotExist:
    print('WARNING: admin group does not exist yet (run bootstrap_roles first)')
" 2>&1 || echo "WARNING: group assignment failed"
fi
echo "Arrancando servidor..."
if [ "$DEBUG" = "True" ]; then
  exec python manage.py runserver 0.0.0.0:8000
else
  exec gunicorn accessledger.wsgi --bind 0.0.0.0:${PORT:-8080} --log-file -
fi

