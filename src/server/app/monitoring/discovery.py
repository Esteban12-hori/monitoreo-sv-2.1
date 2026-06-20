"""
Auto-descubrimiento de red (estilo Zabbix network discovery).

Barre un rango CIDR detectando hosts vivos mediante conexiones TCP a puertos
comunes (rápido y fiable a través de firewalls que filtran ICMP) y, de forma
opcional, ICMP. El barrido es concurrente y está acotado en tamaño para no
convertirse en un escáner masivo.

Las primitivas de red (`_probe_tcp`, `_probe_icmp`) se aíslan a nivel de módulo
para poder mockearlas en tests sin tocar la red real.
"""
import ipaddress
import logging
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Puertos habituales para detectar un host "vivo" cuando no se especifican otros.
DEFAULT_PORTS = (22, 80, 443, 3389, 3306, 5432, 8006)
# Tope defensivo: no permitimos barrer rangos enormes (equivale a /22).
MAX_HOSTS = 1024
MAX_WORKERS = 64


def _probe_tcp(host: str, port: int, timeout: float) -> bool:
    """True si el puerto TCP acepta conexión. Aislado para poder mockearlo."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def _probe_icmp(host: str, timeout: float) -> bool:
    """Ping ICMP de un paquete. Reutiliza el ejecutor agentless hardenizado."""
    from .checks import run_icmp_check
    return run_icmp_check(host, timeout=max(1, int(timeout) + 1)).get("status") == "up"


def _probe_host(host: str, ports, timeout: float, use_icmp: bool) -> dict:
    open_ports = [p for p in ports if _probe_tcp(host, p, timeout)]
    if open_ports:
        return {"host": host, "alive": True, "open_ports": open_ports, "method": "tcp"}
    if use_icmp and _probe_icmp(host, timeout):
        return {"host": host, "alive": True, "open_ports": [], "method": "icmp"}
    return {"host": host, "alive": False, "open_ports": [], "method": None}


def discover_hosts(cidr: str, ports=None, timeout: float = 0.5,
                   use_icmp: bool = True) -> list:
    """
    Descubre hosts vivos en `cidr`. Devuelve solo los vivos:
    [{"host", "open_ports", "method"}]. Lanza HTTP 422 si el CIDR es inválido o
    excede `MAX_HOSTS`.
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        raise HTTPException(status_code=422, detail="CIDR inválido")

    hosts = list(network.hosts()) if network.num_addresses > 1 else [network.network_address]
    if len(hosts) > MAX_HOSTS:
        raise HTTPException(
            status_code=422,
            detail=f"Rango demasiado grande ({len(hosts)} hosts); máximo {MAX_HOSTS}",
        )

    scan_ports = list(ports) if ports else list(DEFAULT_PORTS)
    alive = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, len(hosts)))) as pool:
        futures = {
            pool.submit(_probe_host, str(h), scan_ports, timeout, use_icmp): str(h)
            for h in hosts
        }
        for fut in as_completed(futures):
            try:
                res = fut.result()
            except Exception as e:  # pragma: no cover - defensivo
                logger.warning("Probe de %s falló: %s", futures[fut], e)
                continue
            if res["alive"]:
                alive.append({"host": res["host"], "open_ports": res["open_ports"],
                              "method": res["method"]})
    alive.sort(key=lambda r: ipaddress.ip_address(r["host"]))
    return alive
