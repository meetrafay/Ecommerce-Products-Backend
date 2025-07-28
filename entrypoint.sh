#!/bin/sh

echo "Waiting for database..."

# Wait for the PostgreSQL database to be ready
while ! nc -z db 5432; do
  sleep 1
done

echo "Database is up!"

# Run migrations
python manage.py migrate

# Optional: collect static files
# python manage.py collectstatic --noinput

# Run the application server
exec "$@"
