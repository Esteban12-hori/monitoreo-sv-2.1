import argparse
import json
import platform
import subprocess
import time
from datetime import datetime, timezone
import logging
from pathlib import Path
import psutil
import requests
import importlib.util

# --- Plugin System ---
class AgentPlugin:
    """Base class for all metrics plugins"""
    def collect(self) -> dict:
        raise NotImplementedError

class MemoryPlugin(AgentPlugin):
    def collect(self):
        vm = psutil.virtual_memory()
        return {
            "memory": {
                "total": float(vm.total) / (1024 ** 2),
                "used": float(vm.used) / (1024 ** 2),
                "free": float(vm.available) / (1024 ** 2),
                "cache": float(getattr(vm, "cached", 0)) / (1024 ** 2),
            }
        }

class CPUPlugin(AgentPlugin):
    def collect(self):
        total = psutil.cpu_percent(interval=1)
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        return {"cpu": {"total": total, "per_core": per_core}}

class DiskPlugin(AgentPlugin):
    def collect(self):
        mountpoint = "/"
        try:
            parts = psutil.disk_partitions()
            if parts:
                mountpoint = parts[0].mountpoint or mountpoint
        except Exception:
            pass
        du = psutil.disk_usage(mountpoint)
        return {
            "disk": {
                "total": float(du.total) / (1024 ** 3),
                "used": float(du.used) / (1024 ** 3),
                "free": float(du.free) / (1024 ** 3),
                "percent": du.percent,
            }
        }

class NetworkPlugin(AgentPlugin):
    def __init__(self):
        self.last_sent = 0
        self.last_recv = 0
        self.last_time = 0

    def collect(self):
        net = psutil.net_io_counters()
        current_time = time.time()
        
        sent_rate = 0.0
        recv_rate = 0.0
        
        if self.last_time > 0:
            delta = current_time - self.last_time
            if delta > 0:
                # Handle counter wrap-around or restart (basic check)
                if net.bytes_sent >= self.last_sent and net.bytes_recv >= self.last_recv:
                    sent_rate = (net.bytes_sent - self.last_sent) / delta
                    recv_rate = (net.bytes_recv - self.last_recv) / delta
        
        # Update state
        self.last_sent = net.bytes_sent
        self.last_recv = net.bytes_recv
        self.last_time = current_time

        return {
            "network": {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
                "sent_rate": sent_rate,
                "recv_rate": recv_rate
            }
        }

class UptimePlugin(AgentPlugin):
    def collect(self):
        return {"uptime": time.time() - psutil.boot_time()}

class DockerPlugin(AgentPlugin):
    def collect(self):
        try:
            out = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True)
            names = [n for n in out.strip().split("\n") if n]
            return {"docker": {"running_containers": len(names), "containers": [{"name": n} for n in names]}}
        except Exception:
            return {"docker": {"running_containers": 0, "containers": []}}

class ServicesPlugin(AgentPlugin):
    def collect(self):
        services = []
        try:
            # scan for listening ports (Auto-discovery)
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'LISTEN':
                    try:
                        proc = psutil.Process(conn.pid) if conn.pid else None
                        name = proc.name() if proc else "unknown"
                        # Filtrar procesos comunes de sistema que ensucian
                        if name in ["System", "Idle"]: 
                            continue
                            
                        services.append({
                            "port": conn.laddr.port,
                            "ip": conn.laddr.ip,
                            "name": name,
                            "proto": "tcp" 
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        services.append({
                            "port": conn.laddr.port,
                            "ip": conn.laddr.ip,
                            "name": "unknown",
                            "proto": "tcp"
                        })
            # Deduplicate
            seen = set()
            unique_services = []
            for s in services:
                key = (s['port'], s['name'])
                if key not in seen:
                    seen.add(key)
                    unique_services.append(s)
            return {"services": unique_services}
        except Exception:
            return {"services": []}

class PluginManager:
    def __init__(self):
        self.plugins = []
        # Register built-ins
        self.register(MemoryPlugin())
        self.register(CPUPlugin())
        self.register(DiskPlugin())
        self.register(NetworkPlugin())
        self.register(UptimePlugin())
        self.register(DockerPlugin())
        self.register(ServicesPlugin())
        # Load external
        self.load_external_plugins()
    
    def register(self, plugin: AgentPlugin):
        self.plugins.append(plugin)
    
    def load_external_plugins(self):
        plugins_dir = Path(__file__).resolve().parent / "plugins"
        if not plugins_dir.exists():
            return
        
        for file in plugins_dir.glob("*.py"):
            if file.name.startswith("__"): continue
            try:
                spec = importlib.util.spec_from_file_location(file.stem, file)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                # Look for subclasses of AgentPlugin
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if isinstance(attr, type) and issubclass(attr, AgentPlugin) and attr is not AgentPlugin:
                        self.register(attr())
                        logging.info(f"Loaded external plugin: {attr_name} from {file.name}")
            except Exception as e:
                logging.error(f"Error loading plugin {file.name}: {e}")

    def collect_all(self):
        data = {}
        for p in self.plugins:
            try:
                data.update(p.collect())
            except Exception as e:
                logging.error(f"Error in plugin {p.__class__.__name__}: {e}")
        return data

# --- Main Logic ---

def payload(server_id: str, plugin_manager: PluginManager):
    data = {
        "server_id": server_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    data.update(plugin_manager.collect_all())
    return data

def loop(server_url: str, server_id: str, token: str, interval: int, verify_tls: str):
    plugin_manager = PluginManager()
    logging.info(f"Iniciando bucle de monitoreo. Plugins cargados: {len(plugin_manager.plugins)}")
    
    while True:
        data = payload(server_id, plugin_manager)
        try:
            resp = requests.post(
                f"{server_url}/api/metrics",
                json=data,
                headers={"X-Auth-Token": token},
                timeout=10,
                verify=verify_tls if verify_tls else True,
            )
            if resp.status_code == 200:
                try:
                    rj = resp.json()
                    new_interval = rj.get("report_interval")
                    if new_interval and isinstance(new_interval, int) and new_interval != interval:
                        logging.info("Actualizando intervalo de %ss a %ss", interval, new_interval)
                        interval = new_interval
                except Exception:
                    pass
            else:
                logging.error("Error enviando métricas %s %s", resp.status_code, resp.text)
        except Exception as e:
            logging.exception("Excepción enviando métricas: %s", e)
        time.sleep(interval)


def load_config(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def setup_logging():
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "agent.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    logging.info("Agente iniciado")


def main():
    parser = argparse.ArgumentParser(description="Agente de monitoreo ligero (Modular)")
    parser.add_argument("--server", required=False, help="URL del backend (https://host:port)")
    parser.add_argument("--server-id", required=False, help="Identificador del servidor")
    parser.add_argument("--token", help="Token de autenticación", default="")
    parser.add_argument("--interval", help="Intervalo de envío (segundos)", type=int, default=2400)
    parser.add_argument("--verify", default=None, help="Ruta a CA/cert para verificación TLS (o 'false' para desactivar)")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent / "agent.config.json"), help="Ruta a archivo de configuración")
    args = parser.parse_args()

    setup_logging()
    logging.info("Sistema: %s", platform.platform())

    server = args.server
    server_id = args.server_id
    token = args.token
    interval = args.interval
    verify = args.verify

    cfg = {}
    if not (server and server_id and token):
        cfg = load_config(Path(args.config))

    # Prioridad: Argumento > Config > Default
    server = server or cfg.get("server", "")
    server_id = server_id or cfg.get("server_id", "")
    token = token or cfg.get("token", "")
    
    # Intentar desofuscar token
    try:
        from security import reveal_token
        token = reveal_token(token)
    except ImportError:
        pass

    # Manejo de intervalo
    if args.interval == 2400 and "interval" in cfg:
        interval = cfg.get("interval")

    # Manejo de verify (SSL)
    if verify is None:
        verify = cfg.get("verify", True)
    
    if isinstance(verify, str):
        if verify.lower() == "false":
            verify = False
        elif verify == "":
            verify = True

    if not (server and server_id and token):
        print("Faltan parámetros obligatorios. Usa --config o pasa --server, --server-id y --token.")
        return

    loop(server, server_id, token, interval, verify)


if __name__ == "__main__":
    main()
