#!/bin/bash
# Shortcut script to run run_all.py via Docker (Full Stack)
# Usage: ./docker/run_all.sh [-d] [-b]
#
# Options:
#   -d    Run container in detached mode
#   -b    Build only (don't run)
#
# Note: Run this from the project root:
#   cd /c/Users/moham/Desktop/OptyLab
#   ./visual_quality_dashboard/docker/run_all.sh

set -e

# Get the project root (OptyLab directory)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Project root: $PROJECT_ROOT"
echo "DB directory: $PROJECT_ROOT/DB"

# Build the image
echo ""
echo "Building run_all Docker image..."
docker build -t optylab/run_all:latest -f "$SCRIPT_DIR/Dockerfile.run_all" .

# Check if we should just build
BUILD_ONLY=false
DETACHED=false

while getopts "db" opt; do
  case $opt in
    d) DETACHED=true ;;
    b) BUILD_ONLY=true ;;
  esac
done

if [ "$BUILD_ONLY" = true ]; then
  echo ""
  echo "Build only mode - image built successfully."
  exit 0
fi

# Run the container
echo ""
echo "Running full stack (frontend + backend)..."
if [ "$DETACHED" = true ]; then
  echo ""
  docker run -d --name optylab_run_all \
    -p 8080:80 \
    -p 8000:8000 \
    -v "$PROJECT_ROOT/DB:/app/DB" \
    -v "$PROJECT_ROOT/visual_quality_dashboard/backend/model:/app/model" \
    optylab/run_all:latest
  echo ""
  echo "Container started in detached mode."
  echo "Use 'docker logs -f optylab_run_all' to view logs."
  echo ""
  echo "Access:"
  echo "  - Frontend: http://localhost:8080"
  echo "  - Backend: http://localhost:8000"
else
  echo ""
  docker run --rm --name optylab_run_all \
    -p 8080:80 \
    -p 8000:8000 \
    -v "$PROJECT_ROOT/DB:/app/DB" \
    -v "$PROJECT_ROOT/visual_quality_dashboard/backend/model:/app/model" \
    optylab/run_all:latest
fi