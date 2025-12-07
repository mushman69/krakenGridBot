#!/bin/bash
# Script to clean up disk space on the server before Docker build

echo "=========================================="
echo "Disk Space Cleanup Script"
echo "=========================================="

# Check current disk usage
echo ""
echo "Current disk usage:"
df -h /

echo ""
echo "Cleaning up Docker..."
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f

# Remove build cache
docker builder prune -a -f

echo ""
echo "Cleaning up system packages..."
# Clean apt cache
sudo apt-get clean
sudo apt-get autoclean
sudo apt-get autoremove -y

# Remove old logs
sudo journalctl --vacuum-time=3d

# Clean temporary files
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*

echo ""
echo "Final disk usage:"
df -h /

echo ""
echo "=========================================="
echo "Cleanup complete!"
echo "=========================================="

