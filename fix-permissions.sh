#!/bin/bash
# Script to fix permissions for GridBot data directories
# Run this on the host before starting the container

echo "Fixing permissions for GridBot data directories..."

# Create directories if they don't exist
mkdir -p ./data ./exports ./charts ./logs

# Fix permissions - use 777 to ensure container can write
chmod -R 777 ./data ./exports ./charts ./logs

# Verify permissions
echo "Verifying permissions..."
ls -la | grep -E "(data|exports|charts|logs)"

echo "✅ Permissions fixed! You can now start the container."

