#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing project dependencies..."
pip install -r requirements.txt

if [ -n "$DATABASE_URL" ]; then
    echo "Running database migrations..."
    flask db upgrade || echo "Warning: Database upgrade during build failed, will run on startup."
else
    echo "Notice: DATABASE_URL not set during build phase. Migrations will run at container startup."
fi

echo "Build completed successfully!"

