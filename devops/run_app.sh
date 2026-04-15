#!/bin/sh
set -e

echo Django migrate
python manage.py migrate --noinput

echo Run app
python manage.py runserver 0.0.0.0:8000