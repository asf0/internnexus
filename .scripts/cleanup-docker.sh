#!/bin/sh
# Docker cleanup script: removes old images, build cache, and unused volumes
# Keeps last 2 recent images per service for safe rollback
# Usage: bash cleanup-docker.sh

set -e

echo "=== Docker Cleanup Started ==="
echo ""

# Show disk usage before cleanup
echo "📊 Disk usage BEFORE cleanup:"
docker system df
echo ""

# Remove dangling images (orphaned layers)
echo "🗑️  Removing dangling images..."
DANGLING_COUNT=$(docker images -f "dangling=true" -q | wc -l)
if [ "$DANGLING_COUNT" -gt 0 ]; then
  docker image prune -f --filter "dangling=true"
  echo "   ✓ Removed $DANGLING_COUNT dangling image(s)"
else
  echo "   ✓ No dangling images to remove"
fi
echo ""

# Remove unused build cache
echo "🗑️  Removing unused build cache..."
CACHE_BEFORE=$(docker system df | grep "Build cache" | awk '{print $2}')
docker builder prune -f --filter "unused-for=24h"
echo "   ✓ Build cache pruned (older than 24h)"
echo ""

# Remove unused volumes (older than 24h)
echo "🗑️  Removing unused volumes (older than 24h)..."
VOLUME_COUNT=$(docker volume ls -f "dangling=true" -q | wc -l)
if [ "$VOLUME_COUNT" -gt 0 ]; then
  docker volume prune -f --filter "label!=keep" --filter "until=24h"
  echo "   ✓ Removed $VOLUME_COUNT unused volume(s)"
else
  echo "   ✓ No unused volumes to remove"
fi
echo ""

# Remove untagged images (old builds without tags)
echo "🗑️  Removing untagged images..."
UNTAGGED_COUNT=$(docker images -f "dangling=false" | tail -n +2 | awk '$1 == "<none>" {print $3}' | wc -l)
if [ "$UNTAGGED_COUNT" -gt 0 ]; then
  docker images -f "dangling=false" | tail -n +2 | awk '$1 == "<none>" {print $3}' | xargs -r docker rmi -f 2>/dev/null || true
  echo "   ✓ Removed $UNTAGGED_COUNT untagged image(s)"
else
  echo "   ✓ No untagged images to remove"
fi
echo ""

# Keep last 2 recent images per service
for SERVICE in backend frontend pipeline; do
  echo "📌 Keeping last 2 images for: $SERVICE"
  IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}} {{.ID}} {{.CreatedAt}}" | grep "internnexus-$SERVICE" | sort -k3 -r)
  if [ -z "$IMAGES" ]; then
    echo "   ✓ No images found for $SERVICE"
    continue
  fi
  
  KEEP_COUNT=0
  echo "$IMAGES" | while read -r line; do
    if [ $KEEP_COUNT -lt 2 ]; then
      echo "   ✓ KEEPING: $(echo $line | awk '{print $1}')"
      KEEP_COUNT=$((KEEP_COUNT + 1))
    else
      IMAGE_ID=$(echo $line | awk '{print $2}')
      IMAGE_NAME=$(echo $line | awk '{print $1}')
      # Only remove if not currently in use by a running container
      if ! docker ps --all --quiet --filter "ancestor=$IMAGE_ID" --filter "status=running" --filter "status=paused" | grep -q .; then
        docker rmi "$IMAGE_ID" 2>/dev/null || true
        echo "   🗑️  REMOVED old image: $IMAGE_NAME ($IMAGE_ID)"
      else
        echo "   ⏸️  SKIPPED in-use image: $IMAGE_NAME"
      fi
    fi
  done
done
echo ""

# Final cleanup pass: remove all unused images
echo "🗑️  Running final unused image cleanup..."
FINAL_REMOVED=$(docker image prune -af --filter "until=48h" 2>&1 | grep -i "deleted\|space reclaimed" || echo "None")
echo "   $FINAL_REMOVED"
echo ""

# Show disk usage after cleanup
echo "📊 Disk usage AFTER cleanup:"
docker system df
echo ""

echo "✅ Docker Cleanup Completed Successfully"
