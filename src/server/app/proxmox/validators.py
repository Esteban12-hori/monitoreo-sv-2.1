"""
Validación estricta de entradas para la gestión Proxmox.

TODA entrada que vaya a formar parte de un comando ejecutado por SSH DEBE pasar
por estos validadores. El objetivo es impedir inyección de comandos: solo se
aceptan valores con la forma exacta esperada; cualquier otra cosa produce un
HTTP 422 antes de construir el comando.
"""
import re
from fastapi import HTTPException

# Nombres seguros (snapshots, storages, interfaces, nodos): sin metacaracteres de shell.
_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
# Hostname / IP para SSH.
_HOST_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,255}$")

VALID_GUEST_TYPES = ("qemu", "lxc")
VALID_BACKUP_MODES = ("snapshot", "suspend", "stop")
VALID_AUTH_TYPES = ("password", "key")
# Acciones de ciclo de vida soportadas por qm/pct (allowlist estricta).
VALID_POWER_ACTIONS = ("start", "stop", "shutdown", "reboot", "suspend", "resume")

# Rangos defensivos para recursos hardware.
CORES_MIN, CORES_MAX = 1, 512
MEMORY_MIN_MB, MEMORY_MAX_MB = 16, 4 * 1024 * 1024   # 16 MB .. 4 TB
DISK_RE = re.compile(r"^\+?\d{1,6}[MGT]$")            # ej. "10G", "+5G"


def _fail(detail: str):
    raise HTTPException(status_code=422, detail=detail)


def valid_vmid(vmid) -> int:
    """vmid/ctid debe ser un entero positivo (Proxmox: 100..999999999)."""
    try:
        v = int(vmid)
    except (TypeError, ValueError):
        _fail("vmid inválido: debe ser numérico")
    if v < 1 or v > 999999999:
        _fail("vmid fuera de rango")
    return v


def valid_guest_type(guest_type: str) -> str:
    if guest_type not in VALID_GUEST_TYPES:
        _fail(f"guest_type inválido (esperado {VALID_GUEST_TYPES})")
    return guest_type


def valid_name(name: str, field: str = "name") -> str:
    if not isinstance(name, str) or not _NAME_RE.match(name):
        _fail(f"{field} inválido: solo se permiten [A-Za-z0-9_.-] (1-64)")
    return name


def valid_storage(storage: str) -> str:
    return valid_name(storage, "storage")


def valid_hostname(hostname: str) -> str:
    if not isinstance(hostname, str) or not _HOST_RE.match(hostname):
        _fail("hostname inválido")
    return hostname


def valid_port(port, field: str = "port") -> int:
    try:
        p = int(port)
    except (TypeError, ValueError):
        _fail(f"{field} inválido")
    if p < 1 or p > 65535:
        _fail(f"{field} fuera de rango (1-65535)")
    return p


def valid_backup_mode(mode: str) -> str:
    if mode not in VALID_BACKUP_MODES:
        _fail(f"mode inválido (esperado {VALID_BACKUP_MODES})")
    return mode


def valid_power_action(action: str) -> str:
    if action not in VALID_POWER_ACTIONS:
        _fail(f"acción inválida (esperado {VALID_POWER_ACTIONS})")
    return action


def valid_cores(cores) -> int:
    try:
        c = int(cores)
    except (TypeError, ValueError):
        _fail("cores inválido")
    if c < CORES_MIN or c > CORES_MAX:
        _fail(f"cores fuera de rango ({CORES_MIN}-{CORES_MAX})")
    return c


def valid_memory(memory_mb) -> int:
    try:
        m = int(memory_mb)
    except (TypeError, ValueError):
        _fail("memory inválido")
    if m < MEMORY_MIN_MB or m > MEMORY_MAX_MB:
        _fail(f"memory fuera de rango ({MEMORY_MIN_MB}-{MEMORY_MAX_MB} MB)")
    return m


def valid_disk_size(value: str) -> str:
    """Tamaño de disco tipo '10G' o incremento '+5G' (sufijo M/G/T)."""
    if not isinstance(value, str) or not DISK_RE.match(value):
        _fail("tamaño de disco inválido (ej. '10G', '+5G')")
    return value


def valid_tunnel_ip(ip: str) -> str:
    """IP IPv4 simple para el extremo del túnel WireGuard."""
    if not isinstance(ip, str):
        _fail("IP de túnel inválida")
    parts = ip.split(".")
    if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        _fail("IP de túnel inválida")
    return ip
