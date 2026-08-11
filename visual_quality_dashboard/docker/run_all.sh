#!/bin/bash
# Shortcut script to run OptyLab frontend and backend locally
# This runs using local Node.js and Python (no Docker build needed)
# Usage: ./run_all.sh [-b]  (-b for build-only mode, -s for server only)

set -e

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/visual_quality_dashboard"

echo "=========================================="
echo "OptyLab Local Development Server"
echo "=========================================="
echo "Project root: $PROJECT_ROOT"
echo "Frontend: $FRONTEND_DIR"
echo ""

# Check if build-only mode
BUILD_ONLY=false
SERVER_ONLY=false
while getopts "bs" opt; do
  case $opt in
    b) BUILD_ONLY=true ;;
    s) SERVER_ONLY=true ;;
  esac
done

if [ "$BUILD_ONLY" = true ]; then
  echo "Build mode: Installing dependencies..."
  cd "$FRONTEND_DIR"
  npm install
  pip install -r "$FRONTEND_DIR/backend/requirements.txt" --quiet
  echo "Dependencies installed. Run without -b to start servers."
  exit 0
fi

if [ "$SERVER_ONLY" = true ]; then
  echo "[Backend] Starting FastAPI server..."
  cd "$FRONTEND_DIR/backend"
  exec python -m uvicorn main:app --host 127.0.0.1 --port 8000
fi

# Check if we should use the existing run_all.py or our own implementation
if [ -f "$FRONTEND_DIR/run_all.py" ]; then
  echo "[Orchestrator] Using existing run_all.py..."
  cd "$FRONTEND_DIR"
  exec python run_all.py
else
  echo "[Orchestrator] Starting frontend and backend separately..."
  exec python -c "
import subprocess
import sys
import os

frontend_dir = '$FRONTEND_DIR'
backend_dir = os.path.join(frontend_dir, 'backend')

print('[Frontend] Starting Vite dev server...')
frontend_proc = subprocess.Popen(['npm', 'run', 'dev'], cwd=frontend_dir)

print('[Backend] Starting FastAPI server...')
backend_proc = subprocess.Popen(['python', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'], cwd=backend_dir)

print()
print('==========================================')
print('Servers started!')
print('==========================================')
print('Frontend: http://localhost:5173')
print('Backend:  http://localhost:8000')
print()
print('Press Ctrl+C to stop both servers')
print()

try:
    import signal
    def cleanup(signum, frame):
        print('\\n[Orchestrator] Shutting down...')
        frontend_proc.terminate()
        backend_proc.terminate()
        sys.exit(0)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    frontend_proc.wait()
    backend_proc.wait()
except Exception as e:
    frontend_proc.terminate()
    backend_proc.terminate()
    raise
"