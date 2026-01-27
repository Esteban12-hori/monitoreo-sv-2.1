#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
CLIENT_DIR = SRC_DIR / "client"
SERVER_DIR = SRC_DIR / "server"
VENV_DIR = ROOT_DIR / ".venv"

def print_step(msg):
    print(f"\n{'='*50}")
    print(f"==> {msg}")
    print(f"{'='*50}")

def run_command(cmd, cwd=None, env=None, shell=False):
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        subprocess.check_call(cmd, cwd=cwd, env=env, shell=shell)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        sys.exit(1)

def check_requirements():
    print_step("Checking Requirements")
    
    # Check Python
    print(f"Python version: {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        print("Error: Python 3.10+ is required.")
        sys.exit(1)
        
    # Check Node.js
    try:
        node_version = subprocess.check_output(["node", "--version"]).decode().strip()
        print(f"Node.js version: {node_version}")
    except FileNotFoundError:
        print("Warning: Node.js not found. Frontend build will be skipped (unless using Docker).")
        
    # Check Docker (optional)
    try:
        docker_version = subprocess.check_output(["docker", "--version"]).decode().strip()
        print(f"Docker version: {docker_version}")
    except FileNotFoundError:
        print("Docker not found (optional).")

def setup_backend():
    print_step("Setting up Backend")
    
    # Create venv
    if not VENV_DIR.exists():
        print("Creating virtual environment...")
        run_command([sys.executable, "-m", "venv", str(VENV_DIR)])
    else:
        print("Virtual environment already exists.")
    
    # Determine pip/python paths
    if os.name == "nt":
        pip_cmd = str(VENV_DIR / "Scripts" / "pip.exe")
        python_cmd = str(VENV_DIR / "Scripts" / "python.exe")
    else:
        pip_cmd = str(VENV_DIR / "bin" / "pip")
        python_cmd = str(VENV_DIR / "bin" / "python")
        
    # Install dependencies
    print("Installing backend dependencies...")
    run_command([python_cmd, "-m", "pip", "install", "--upgrade", "pip"])
    run_command([pip_cmd, "install", "-r", str(SERVER_DIR / "requirements.txt")])
    
    # Initialize DB (run reset script or similar)
    print("Initializing Database...")
    # Add root to pythonpath for the script
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR)
    
    # Check if DB exists, if not run reset_users to create admin
    db_path = ROOT_DIR / "data" / "monitor.db"
    if not db_path.exists():
         print("Database not found. Creating default admin user...")
         run_command([python_cmd, str(SERVER_DIR / "scripts" / "reset_users.py")], env=env)
    else:
         print("Database exists. Skipping user reset.")

def setup_frontend():
    print_step("Setting up Frontend")
    
    if not CLIENT_DIR.exists():
        print("Client directory not found!")
        return

    # Check for npm
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    try:
        subprocess.check_call([npm_cmd, "--version"], stdout=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("npm not found. Skipping frontend setup.")
        return

    print("Installing frontend dependencies...")
    run_command([npm_cmd, "install"], cwd=str(CLIENT_DIR), shell=True)
    
    print("Building frontend...")
    run_command([npm_cmd, "run", "build"], cwd=str(CLIENT_DIR), shell=True)

def create_env_file():
    print_step("Creating .env file")
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        print("Creating .env from template...")
        with open(env_path, "w") as f:
            f.write("ENV=development\n")
            f.write("ENCRYPTION_KEY=ZcTj8yXQ5zK9r1w2e3r4t5y6u7i8o9p0a1s2d3f4g5h=\n")
            f.write("# SMTP Config (Optional)\n")
            f.write("# SMTP_SERVER=\n")
            f.write("# SMTP_PORT=\n")
        print(".env file created.")
    else:
        print(".env file already exists.")

def main():
    print_step("UpKeep - Installer")
    
    check_requirements()
    create_env_file()
    
    setup_backend()
    
    try:
        setup_frontend()
    except Exception as e:
        print(f"Frontend setup failed: {e}")
        print("You can try building it manually inside src/client")

    print_step("Installation Complete!")
    print("\nTo run the backend:")
    if os.name == "nt":
        print(f"  {VENV_DIR}\\Scripts\\python.exe -m uvicorn src.server.app.main:app --reload")
    else:
        print(f"  {VENV_DIR}/bin/python -m uvicorn src.server.app.main:app --reload")
        
    print("\nTo run the frontend (dev mode):")
    print(f"  cd src/client && npm run dev")
    
    print("\nOr use Docker:")
    print("  docker-compose up --build")

if __name__ == "__main__":
    main()
