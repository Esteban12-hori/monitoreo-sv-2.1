__SERVER_URL__ = ""  # This will be injected by the backend

import sys
import os
import platform
import json
import re
import time
import subprocess
import argparse
import socket
import uuid
from pathlib import Path
import urllib.request

# Configuration
AGENT_FILENAME = "agent.py"
CONFIG_FILENAME = "agent.config.json"
DEFAULT_INSTALL_DIR = Path.home() / "monitoreo-agent"

def print_step(title):
    print("\n==> " + title)

def get_input(prompt, default=None):
    if default:
        p = f"{prompt} [{default}]: "
    else:
        p = f"{prompt}: "
    val = input(p).strip()
    return val if val else default

def ensure_packages(packages):
    missing = []
    for p in packages:
        try:
            __import__(p)
        except Exception:
            missing.append(p)
    if not missing:
        return True
    print_step(f"Instalando dependencias Python: {', '.join(missing)}")
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + missing
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError:
        print("Instalación estándar fallida. Intentando con --break-system-packages...")
        try:
            cmd_force = cmd + ["--break-system-packages"]
            subprocess.check_call(cmd_force)
            return True
        except subprocess.CalledProcessError:
            print("Error instalando paquetes. Instálalos manualmente.")
            return False

def download_file(url, dest):
    try:
        print(f"Descargando {url} -> {dest} ...")
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        print(f"Error descargando {url}: {e}")
        return False

def setup_systemd(install_dir, python_exec):
    print_step("Configurando servicio systemd (Linux)")
    if platform.system() != "Linux":
        print("No es Linux, saltando configuración systemd.")
        return

    service_name = "monitoreo-agent.service"
    service_path = f"/etc/systemd/system/{service_name}"
    
    content = f"""[Unit]
Description=Monitoreo Agent
After=network.target

[Service]
Type=simple
User={os.getlogin()}
WorkingDirectory={install_dir}
ExecStart={python_exec} {install_dir}/{AGENT_FILENAME}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    try:
        # Check sudo access
        if os.geteuid() != 0:
            print("Se requieren permisos de root para instalar el servicio systemd.")
            print("Ejecuta el siguiente comando manualmente para crear el servicio:")
            print(f"\nsudo tee {service_path} <<EOF\n{content}EOF")
            print(f"\nsudo systemctl daemon-reload && sudo systemctl enable --now {service_name}")
            return

        with open(service_path, "w") as f:
            f.write(content)
        
        subprocess.check_call(["systemctl", "daemon-reload"])
        subprocess.check_call(["systemctl", "enable", "--now", service_name])
        print(f"Servicio {service_name} instalado y arrancado.")
    except Exception as e:
        print(f"Error configurando systemd: {e}")

def setup_windows_persistence(install_dir, python_exec):
    print_step("Configurando persistencia en Windows")
    if platform.system() != "Windows":
        return

    # Option 1: Startup Folder (User level)
    # Option 2: Task Scheduler (System level - preferred for servers)
    
    method = get_input("¿Método de inicio? [1] Carpeta Inicio (Usuario), [2] Tarea Programada (Sistema)", "2")
    
    agent_script = install_dir / AGENT_FILENAME
    
    if method == "1":
        import winshell  # Might not be available, use os path
        startup_dir = Path(os.getenv("APPDATA")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        bat_path = startup_dir / "monitoreo_agent.bat"
        try:
            with open(bat_path, "w") as f:
                f.write(f'@echo off\ncd "{install_dir}"\n"{python_exec}" "{agent_script}"\n')
            print(f"Acceso directo creado en: {bat_path}")
        except Exception as e:
            print(f"Error creando acceso directo: {e}")
            
    else:
        # Task Scheduler
        task_name = "MonitoreoAgent"
        # Run whether user is logged on or not, with highest privileges
        # We need to wrap it in a .bat or .vbs to avoid window popup if possible, 
        # but for simplicity we run python directly.
        # Actually, pythonw.exe is better for no-window.
        
        python_w = python_exec.replace("python.exe", "pythonw.exe")
        if not os.path.exists(python_w):
            python_w = python_exec
            
        cmd_str = f'"{python_w}" "{agent_script}"'
        
        # schtasks /create /tn "MonitoreoAgent" /tr "..." /sc onstart /ru SYSTEM /f
        # Note: /ru SYSTEM requires Admin privileges.
        
        try:
            subprocess.check_call([
                "schtasks", "/create", "/tn", task_name, 
                "/tr", cmd_str, 
                "/sc", "onstart", 
                "/ru", "SYSTEM", 
                "/f"  # Force overwrite
            ])
            print(f"Tarea programada '{task_name}' creada exitosamente.")
            print("El agente iniciará automáticamente al arrancar el sistema.")
            
            # Start it now?
            start_now = get_input("¿Iniciar ahora? (s/n)", "s").lower()
            if start_now == "s":
                subprocess.check_call(["schtasks", "/run", "/tn", task_name])
                print("Tarea iniciada.")
                
        except subprocess.CalledProcessError:
            print("Error creando tarea programada. Asegúrate de ejecutar como Administrador.")
            print("Alternativa: Intenta con el método 1 (Carpeta Inicio).")

def main():
    print("🚀 Iniciando instalación de Agente de Monitoreo")
    
    # 1. Prepare Directory
    install_dir_str = get_input("Directorio de instalación", str(DEFAULT_INSTALL_DIR))
    install_dir = Path(install_dir_str).expanduser().resolve()
    
    if not install_dir.exists():
        try:
            install_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error creando directorio {install_dir}: {e}")
            return

    print(f"Instalando en: {install_dir}")

    # 2. Determine Source
    # If __SERVER_URL__ is set, we download agent.py from there.
    # Otherwise, we look for agent.py locally.
    server_url = __SERVER_URL__
    local_agent_path = Path(__file__).parent / AGENT_FILENAME
    
    target_agent_path = install_dir / AGENT_FILENAME
    
    if server_url:
        print(f"Modo remoto detectado. Servidor: {server_url}")
        download_url = f"{server_url}/api/agent/download"
        if not download_file(download_url, target_agent_path):
            print("Fallo la descarga del agente. Abortando.")
            return
    elif local_agent_path.exists():
        print("Modo local detectado. Copiando agente...")
        import shutil
        shutil.copy(local_agent_path, target_agent_path)
    else:
        print("No se encuentra agent.py localmente ni se configuró URL remota.")
        # Ask user for URL?
        server_url = get_input("URL del servidor (ej. http://localhost:8000)")
        if server_url:
             download_url = f"{server_url.rstrip('/')}/api/agent/download"
             if not download_file(download_url, target_agent_path):
                return
        else:
            return

    # 3. Dependencies
    ensure_packages(["psutil", "requests"])

    # 4. Configuration
    server_url = server_url or get_input("URL del servidor (ej. http://localhost:8000)", "http://localhost:8000")
    server_id = get_input("ID de este servidor (nombre único)", socket.gethostname())
    token = get_input("Token de autenticación (Dashboard -> Servidores -> Token)")
    
    config = {
        "server": server_url,
        "server_id": server_id,
        "token": token,
        "interval": 10,
        "verify": True
    }
    
    config_path = install_dir / CONFIG_FILENAME
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"Configuración guardada en {config_path}")

    # 5. Service
    if platform.system() == "Linux":
        setup_service = get_input("¿Instalar como servicio systemd? (s/n)", "n").lower()
        if setup_service == "s" or setup_service == "y":
            setup_systemd(install_dir, sys.executable)
    elif platform.system() == "Windows":
        setup_service = get_input("¿Instalar persistencia (auto-inicio)? (s/n)", "n").lower()
        if setup_service == "s" or setup_service == "y":
            setup_windows_persistence(install_dir, sys.executable)
    
    print("\n✅ Instalación completada.")
    print(f"Para ejecutar manualmente:\n  cd {install_dir}\n  {sys.executable} {AGENT_FILENAME}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado.")
