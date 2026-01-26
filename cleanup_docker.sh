#!/bin/bash

# Docker Cleanup Script for VPS
# This script frees up disk space by cleaning Docker resources

echo "=========================================="
echo "Docker Cleanup Script"
echo "=========================================="
echo ""

# Check disk space before
echo "Disk space BEFORE cleanup:"
df -h /
echo ""

# Check Docker disk usage
echo "Docker disk usage:"
docker system df
echo ""

# Ask for confirmation
echo "This will remove:"
echo "  - All stopped containers"
echo "  - All unused images"
echo "  - All unused networks"
echo "  - All build cache"
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled"
    exit 1
fi

# Remove stopped containers
echo "Removing stopped containers..."
docker container prune -f

# Remove unused images
echo "Removing unused images..."
docker image prune -a -f

# Remove unused volumes
echo "Removing unused volumes..."
docker volume prune -f

# Remove unused networks
echo "Removing unused networks..."
docker network prune -f

# Remove build cache
echo "Removing build cache..."
docker builder prune -a -f

# Full system cleanup
echo "Performing full system cleanup..."
docker system prune -a --volumes -f

# Check disk space after
echo ""
echo "Disk space AFTER cleanup:"
df -h /
echo ""

# Check Docker disk usage after
echo "Docker disk usage AFTER cleanup:"
docker system df
echo ""

echo "=========================================="
echo "Cleanup completed!"
echo "=========================================="
