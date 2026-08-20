#!/usr/bin/env bash

set -e

python manage.py collectstatic --noinput
python manage.py migrate --noinput
exec python -m gunicorn --bind 0.0.0.0:8000 --workers 3 main.wsgi:application
