import subprocess
import os
import sys
import shutil

# Always use Python 3.14 where fastapi and other dependencies are installed
PYTHON = r"C:/Python314/python.exe"

def cleanup_cache():
    print("[Orchestrator] Cleaning up uploads folder and results...")
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    uploads_dir = os.path.join(backend_dir, "uploads")
    heatmaps_dir = os.path.join(backend_dir, "heatmaps")
    results_file = os.path.join(backend_dir, "results.json")
    
    # Clear folders
    for target_dir in [uploads_dir, heatmaps_dir]:
        if os.path.exists(target_dir):
            for filename in os.listdir(target_dir):
                file_path = os.path.join(target_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"[Orchestrator] Failed to delete {file_path}. Reason: {e}")
                
    # Clear results.json
    if os.path.exists(results_file):
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                f.write("[]")
        except Exception as e:
            print(f"[Orchestrator] Failed to clear results.json. Reason: {e}")

def run_backend():
    print("[Backend] Installing requirements...")
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")

    # Install requirements using the correct Python
    # Use --no-cache-dir and --disable-pip-version-check to speed up and avoid issues
    result = subprocess.run(
        [PYTHON, "-m", "pip", "install", "-r", "requirements.txt", "--no-cache-dir", "--disable-pip-version-check"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )
    if result.returncode != 0:
        print(f"[Backend] Warning: pip install had issues (return code {result.returncode})")
        print(f"[Backend] stderr: {result.stderr[-1000:] if result.stderr else 'None'}")
    else:
        print("[Backend] Requirements installed successfully.")

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
    
    # Always ensure we start with a clean slate
    cleanup_cache()
    
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
        
        cleanup_cache()
