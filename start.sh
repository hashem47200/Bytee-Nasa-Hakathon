#!/usr/bin/env bash
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python) || { echo "Python 3.10+ is required."; exit 1; }
$PY -c "import django" 2>/dev/null || $PY -m pip install -r requirements.txt
$PY manage.py migrate --noinput
$PY manage.py import_missions
$PY manage.py collectstatic --noinput
echo "============================================================"
echo "  NASA EXPLORER HUB - PRODUCTION READY"
echo "  Serving at: http://127.0.0.1:8123"
echo "============================================================"
if command -v gunicorn &>/dev/null; then
  exec gunicorn nasa_hub.wsgi:application --bind 0.0.0.0:8123 --workers 3
else
  exec $PY manage.py runserver 0.0.0.0:8123
fi
