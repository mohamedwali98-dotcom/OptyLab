import subprocess
import os
import sys
import shutil

# ── Configuration ─────────────────────────────────────────────────────────────
# Path to docker-compose.yml
COMPOSE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docker-compose.yml")

# Only these OptyLab services will ever be started by this script.
OPTYLAB_SERVICES = ["backend", "frontend"]

def get_compose_cmd():
    """Return the docker-compose command (docker-compose or docker compose)."""
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    elif shutil.which("docker"):
        return ["docker", "compose"]
    else:
        print("[Docker] ERROR: Docker is not installed or not in PATH.", file=sys.stderr)
        sys.exit(1)

def run_docker_compose():
    """Build and start ONLY the OptyLab services defined in docker-compose.yml."""
    print("[Docker] Building and starting OptyLab services:", ", ".join(OPTYLAB_SERVICES), "\n")

    compose_cmd = get_compose_cmd()

    # Build and start ONLY the OptyLab services in the foreground.
    # Using explicit service names guarantees containers from other
    # projects/images are never started.
    try:
        subprocess.run(
            compose_cmd + ["-f", COMPOSE_FILE, "up", "--build"] + OPTYLAB_SERVICES,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"[Docker] docker-compose failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n[Docker] Shutting down OptyLab containers...")
        subprocess.run(compose_cmd + ["-f", COMPOSE_FILE, "down"])
        print("[Docker] OptyLab containers stopped.")

if __name__ == "__main__":
    print("Starting OptyLab Visual Quality Dashboard via Docker...\n")
    run_docker_compose()