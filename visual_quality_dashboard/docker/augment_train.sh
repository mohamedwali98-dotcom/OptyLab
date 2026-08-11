#!/bin/bash
# Shortcut script to run augment_and_train.py via Docker
# Usage: ./docker/augment_train.sh [args...]
# 
# Note: This script should be run from the project root:
#   cd /c/Users/moham/Desktop/OptyLab
#   ./visual_quality_dashboard/docker/augment_train.sh

set -e

# Get the project root (OptyLab directory)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Project root: $PROJECT_ROOT"
echo "DB directory: $PROJECT_ROOT/DB"

# Default values
AUG_PER_IMAGE=${AUG_PER_IMAGE:-10}

# Build the image
echo ""
echo "Building augment_train Docker image..."
docker build -t optylab/augment_train:latest -f "$SCRIPT_DIR/Dockerfile.augment_train" .

# Run the container
echo ""
echo "Running augment_and_train.py..."
echo "  - DB data: $PROJECT_ROOT/DB → /app/DB"
echo "  - Model output: $PROJECT_ROOT/visual_quality_dashboard/backend/model → /app/model"
echo ""
docker run --rm \
  -e AUG_PER_IMAGE="$AUG_PER_IMAGE" \
  -v "$PROJECT_ROOT/DB:/app/DB" \
  -v "$PROJECT_ROOT/visual_quality_dashboard/backend/model:/app/model" \
  optylab/augment_train:latest