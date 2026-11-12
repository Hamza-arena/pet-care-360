#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing project dependencies..."
pip install -r requirements.txt

echo "Running database migrations..."
flask db upgrade

echo "Build completed successfully!"

