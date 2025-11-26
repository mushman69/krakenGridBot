#!/bin/bash
# Docker entrypoint script to ensure proper permissions

# Fix permissions for data directories
chmod -R 777 /app/data /app/exports /app/charts /app/logs 2>/dev/null || true

# Ensure directories exist
mkdir -p /app/data /app/exports /app/charts /app/logs

# Set permissions again after creation
chmod -R 777 /app/data /app/exports /app/charts /app/logs 2>/dev/null || true

# Execute the main command
exec "$@"

