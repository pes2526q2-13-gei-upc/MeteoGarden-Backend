#!/bin/sh
set -e

echo Django migrate
python manage.py migrate --noinput

echo Django Collectstatic
python manage.py collectstatic --noinput --clear

echo Run app
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --access-logfile - --error-logfile -