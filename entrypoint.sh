#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Execute the main container command passed from CMD
echo "Starting application server..."
exec "$@"
