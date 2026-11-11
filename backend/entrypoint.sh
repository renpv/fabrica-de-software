#!/bin/sh
# Aplica as migrações e entrega o processo ao comando da imagem (gunicorn).
set -eu
python manage.py migrate --noinput
exec "$@"
