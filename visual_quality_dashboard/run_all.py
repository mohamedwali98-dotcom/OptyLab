import subprocess
import os
import sys

# Always use Python 3.14 where fastapi and other dependencies are installed
PYTHON = r"C:/Python314/python.exe"

def run_backend():
    print("[Backend] Installing requirements...")
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")

    # Install requirements using the correct Python
    subprocess.run([PYTHON, "-m", "pip", "install", "-r", "requirements.txt"], cwd=backend_dir)

    print("[Backend] Starting FastAPI server on port 8000...")
    process = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "main:app", "--reload", "--port", "8000"],
        cwd=backend_dir
    )
    return process

def run_frontend():
    print("[Frontend] Starting Vite dev server...")
    root_dir = os.path.dirname(__file__)
    
    # Use npm.cmd on Windows, npm on other OS
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    
    # Start Vite server
    process = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=root_dir
    )
    return process

if __name__ == "__main__":
    print("Starting OptyLab Visual Quality Dashboard Orchestration...\n")
    
    backend_proc = run_backend()
    frontend_proc = run_frontend()
    
    try:
        # Keep the script running while servers are running
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\n[Orchestrator] Shutting down servers...")
        backend_proc.terminate()
        frontend_proc.terminate()
        
        backend_proc.wait()
        frontend_proc.wait()
        print("[Orchestrator] All servers stopped.")
