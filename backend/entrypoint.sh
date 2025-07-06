#!/usr/bin/env bash
set -e

echo "⏳ waiting for postgres: $POSTGRES_HOST:$POSTGRES_PORT ..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  sleep 2
done
echo "✅ postgres is ready"

echo "applying migrations"
python manage.py migrate --noinput

echo " loading components"
python manage.py create_data

echo "starting gunicorn"
exec gunicorn foodgram.wsgi:application --bind 0.0.0.0:8000
