"""
Universal Launcher for Nepal Terai Flood Intelligence System.
Launches the FastAPI geospatial backend (port 8000) and the Vite React frontend (port 5173).
"""

import subprocess
import sys
import os
import time

def main():
    print("================================================================")
    print("   NEPAL TERAI FLOOD INTELLIGENCE SYSTEM — COMMAND CENTER       ")
    print("   Problem Statement 01: Rapid Flood Extent Mapping & Impacts   ")
    print("================================================================\n")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(base_dir, "frontend")

    print("[1/2] Starting FastAPI Geospatial Engine on http://localhost:8000...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=base_dir
    )

    time.sleep(2)

    print("[2/2] Starting Vite Frontend on http://localhost:5173...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=frontend_dir,
        shell=(sys.platform == "win32")
    )

    print("\nSystem running! Press Ctrl+C in this terminal to shut down both servers.")
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
