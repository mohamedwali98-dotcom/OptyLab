"""
run_all.py
==========
One-command launcher for the OptyLab dashboard.

Default (no flags) — LOCAL, no Docker, no image build:
    python run_all.py
        Starts the FastAPI backend (uvicorn, :8000) and the Vite frontend
        dev server (:5173) as local subprocesses, using the same Python
        that is running this script and whatever `npm` is on PATH. Nothing
        is containerized and nothing gets built.

Flags:
    --train           Run augment_and_train.py to completion first (augments
                       DB/RawImages{Good,Damaged} -> DB/Good|Damaged, then
                       retrains the SVM+CNN+ViT ensemble), then serve.
    --docker          Serve via `docker compose up` instead of local
                       processes. Images are built only if they don't exist
                       yet — this does NOT rebuild on every launch.
    --docker --build  Force a Docker image rebuild before starting.

Examples:
    python run_all.py
    python run_all.py --train
    python run_all.py --docker
    python run_all.py --docker --build
"""

import argparse
import importlib.util
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR     = Path(__file__).resolve().parent   # visual_quality_dashboard/
BACKEND_DIR  = ROOT_DIR / "backend"
COMPOSE_FILE = ROOT_DIR / "docker-compose.yml"

# Only these OptyLab services will ever be started by the --docker path.
OPTYLAB_SERVICES = ["backend", "frontend"]


# ── Docker path ────────────────────────────────────────────────────────────
def get_compose_cmd():
    """Return the docker-compose command (docker-compose or docker compose)."""
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    elif shutil.which("docker"):
        return ["docker", "compose"]
    else:
        print("[Docker] ERROR: Docker is not installed or not in PATH.", file=sys.stderr)
        sys.exit(1)


def run_docker_compose(build: bool):
    """Start the OptyLab services defined in docker-compose.yml. Compose
    builds an image only if it doesn't exist yet unless --build is passed —
    this launcher never forces a rebuild on every run."""
    compose_cmd = get_compose_cmd()
    up_cmd = compose_cmd + ["-f", str(COMPOSE_FILE), "up"]
    if build:
        up_cmd.append("--build")
    up_cmd += OPTYLAB_SERVICES

    mode = "Building and starting" if build else "Starting (building only if images are missing)"
    print(f"[Docker] {mode}:", ", ".join(OPTYLAB_SERVICES), "\n")
    try:
        subprocess.run(up_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[Docker] docker-compose failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n[Docker] Shutting down OptyLab containers...")
        subprocess.run(compose_cmd + ["-f", str(COMPOSE_FILE), "down"])
        print("[Docker] OptyLab containers stopped.")


# ── Local path (no Docker) ──────────────────────────────────────────────────
def _check_backend_deps():
    if importlib.util.find_spec("uvicorn") is None:
        print(f"[Backend] ERROR: 'uvicorn' is not installed for this Python ({sys.executable}).",
              file=sys.stderr)
        print(f"          Run:  {sys.executable} -m pip install -r backend/requirements.txt",
              file=sys.stderr)
        sys.exit(1)


def _ensure_frontend_deps():
    npm = shutil.which("npm")
    if npm is None:
        print("[Frontend] ERROR: 'npm' was not found on PATH. Install Node.js "
              "from https://nodejs.org and re-run.", file=sys.stderr)
        sys.exit(1)
    if not (ROOT_DIR / "node_modules").exists():
        print("[Frontend] node_modules/ not found — running npm install...\n")
        subprocess.run([npm, "install"], cwd=str(ROOT_DIR), check=True)
    return npm


def run_training():
    """Run augment_and_train.py to completion. Exits the whole script if
    training fails, rather than going on to serve a stale or half-written
    model."""
    _check_backend_deps()
    script = BACKEND_DIR / "augment_and_train.py"
    print("[Train] Running augment_and_train.py (this can take a while — CNN/ViT "
          "now train with early stopping)...\n")
    result = subprocess.run([sys.executable, str(script)], cwd=str(BACKEND_DIR))
    if result.returncode != 0:
        print(f"\n[Train] ERROR: training failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def _kill_process_tree(proc: subprocess.Popen):
    """Terminate a process and, on Windows, its full descendant tree.
    `npm run dev` on Windows spawns Vite as a grandchild that a plain
    proc.terminate() (which only signals the direct npm.cmd child) can leave
    running as an orphan on port 5173 — taskkill /T walks the whole tree."""
    if proc.poll() is not None:
        return
    if platform.system() == "Windows":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def run_local():
    """Start the backend (uvicorn) and frontend (vite) as local subprocesses
    — no Docker involved. Both inherit this process's stdout/stderr so their
    logs interleave live in the terminal."""
    _check_backend_deps()
    npm = _ensure_frontend_deps()

    print("[Local] Starting backend  -> http://127.0.0.1:8000")
    print("[Local] Starting frontend -> http://localhost:5173")
    print("[Local] Press Ctrl+C to stop both.\n")

    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(BACKEND_DIR),
    )
    frontend_proc = subprocess.Popen(
        [npm, "run", "dev"],
        cwd=str(ROOT_DIR),
    )

    try:
        while backend_proc.poll() is None and frontend_proc.poll() is None:
            time.sleep(0.5)
        if backend_proc.poll() is not None:
            print(f"\n[Local] Backend exited (code {backend_proc.returncode}); stopping frontend...")
        else:
            print(f"\n[Local] Frontend exited (code {frontend_proc.returncode}); stopping backend...")
    except KeyboardInterrupt:
        print("\n[Local] Shutting down...")
    finally:
        _kill_process_tree(backend_proc)
        _kill_process_tree(frontend_proc)
        print("[Local] Stopped.")


def main():
    parser = argparse.ArgumentParser(description="Run the OptyLab dashboard.")
    parser.add_argument("--train", action="store_true",
                         help="Run augment_and_train.py before serving.")
    parser.add_argument("--docker", action="store_true",
                         help="Serve via docker compose instead of local processes.")
    parser.add_argument("--build", action="store_true",
                         help="With --docker, force a Docker image rebuild.")
    args = parser.parse_args()

    if args.train:
        run_training()

    if args.docker:
        run_docker_compose(build=args.build)
    else:
        run_local()


if __name__ == "__main__":
    main()
