#!/usr/bin/env python
"""
CutFlow Studio Unified Launcher
Starts both the Python API backend and the Vite frontend with one command.
"""

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
WEB_DIR = ROOT_DIR / "web"

if sys.platform == "win32":
    VENV_PYTHON = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
else:
    VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python"

# Fall back to currently active Python if run within a virtualenv
if not VENV_PYTHON.exists() and (sys.prefix != sys.base_prefix or ".venv" in sys.executable.lower()):
    VENV_PYTHON = Path(sys.executable)


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def free_port(port: int):
    """If port is occupied by an orphaned process, attempt to free it."""
    if not is_port_in_use(port):
        return
    print(f"⚠️  Port {port} is occupied by an existing process. Freeing port...")
    try:
        if sys.platform == "win32":
            res = subprocess.run(
                ["powershell", "-Command", f"(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue).OwningProcess"],
                capture_output=True, text=True
            )
            for pid_str in res.stdout.strip().split():
                if pid_str.isdigit() and int(pid_str) != os.getpid():
                    subprocess.run(["taskkill", "/F", "/PID", pid_str], capture_output=True)
            time.sleep(1)
        else:
            subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
            time.sleep(1)
    except Exception:
        pass


def check_prerequisites():
    if not VENV_PYTHON.exists():
        print(f"❌ Virtual environment python not found at: {VENV_PYTHON}")
        print("   Please create .venv first or activate your virtual environment.")
        sys.exit(1)
    if not WEB_DIR.exists():
        print(f"❌ Web directory not found at: {WEB_DIR}")
        sys.exit(1)


def main():
    check_prerequisites()

    # Free backend port if an old orphaned process is still running
    free_port(8000)

    print("\n" + "=" * 65)
    print("🎬 CutFlow Studio — AI Video Prep & Smart Editor")
    print("=" * 65)
    print("🚀 Starting Backend API Server (Port 8000)...")
    print("⚡ Starting Vite React Frontend (Port 3000)...")
    print("=" * 65 + "\n")

    # Start FastAPI Backend (inherits stdout/stderr so logs stream to console)
    backend_cmd = [str(VENV_PYTHON), "-m", "cutflow.cli", "web", "--port", "8000"]
    backend_proc = subprocess.Popen(backend_cmd, cwd=str(ROOT_DIR))

    # Start Vite Frontend (inherits stdout/stderr so logs stream to console)
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen([npm_cmd, "run", "dev"], cwd=str(WEB_DIR))

    # Wait for servers to initialize
    time.sleep(2)
    try:
        webbrowser.open("http://localhost:3000")
    except Exception:
        pass

    print("\n✅ CutFlow Studio is running!")
    print("👉 Frontend: http://localhost:3000")
    print("👉 Backend API: http://127.0.0.1:8000")
    print("\n💡 Press Ctrl+C to stop both servers.\n")

    try:
        while True:
            time.sleep(0.5)
            # Check if backend crashed
            if backend_proc.poll() is not None:
                print(f"\n❌ Backend server stopped unexpectedly (exit code {backend_proc.returncode}).")
                break
            # Check if frontend crashed
            if frontend_proc.poll() is not None:
                print(f"\n❌ Frontend dev server stopped unexpectedly (exit code {frontend_proc.returncode}).")
                break
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
    finally:
        if frontend_proc.poll() is None:
            frontend_proc.terminate()
            frontend_proc.wait()
        if backend_proc.poll() is None:
            backend_proc.terminate()
            backend_proc.wait()
        print("✅ Servers stopped cleanly.")


if __name__ == "__main__":
    main()
