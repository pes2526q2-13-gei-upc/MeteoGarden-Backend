#!/bin/sh
set -e

echo Django migrate
python manage.py migrate --noinput

echo Seed initial data
python manage.py seed_initial_data

echo Django Collectstatic
python manage.py collectstatic --noinput --clear

echo Run app
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --access-logfile - --error-logfile -