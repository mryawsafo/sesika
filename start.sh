#!/bin/bash
set -e
cd "$(dirname "$0")"
source venv/bin/activate
python manage.py migrate --run-syncdb
python manage.py runserver
