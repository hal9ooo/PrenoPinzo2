#!/bin/bash
set -e

echo "=== PrenoPinzo Entrypoint ==="

# Create data and media directories if they don't exist
mkdir -p /app/data /app/media
chown -R appuser:appuser /app/data /app/media

# Dump environment variables for cron
printenv > /etc/environment

# Start cron
echo "Starting cron..."
service cron start

# Run database migrations and static collection as appuser
echo "Running database migrations..."
gosu appuser python manage.py migrate --noinput

echo "Collecting static files..."
gosu appuser python manage.py collectstatic --noinput

echo "Starting application..."
exec gosu appuser "$@"
