"""
Operaciones de alto nivel sobre nodos Proxmox.

Cada función:
  1) valida estrictamente sus entradas (validators),
  2) construye una lista de argumentos (nunca un string interpolado),
  3) la ejecuta a través de `ssh_executor.run_command`.

Mapa de CLI: qemu -> `qm`, lxc -> `pct`.
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException

from . import ssh_executor
from . import validators as v

logger = logging.getLogger(__name__)


def _cli(guest_type: str) -> str:
    return "qm" if guest_type == "qemu" else "pct"


def _check_rc(rc: int, out: str, err: str, action: str):
    if rc != 0:
        detail = (err or out or "error desconocido").strip()
        raise HTTPException(status_code=502, detail=f"Proxmox '{action}' falló: {detail}")


# --- 1. Recursos hardware ---------------------------------------------------

def set_resources(node, vmid, guest_type: str, cores: Optional[int] = None,
                  memory: Optional[int] = None, disk: Optional[str] = None,
                  disk_size: Optional[str] = None) -> str:
    """
    Modifica recursos de una VM (qemu) o contenedor (lxc).
    cores/memory opcionales; disk+disk_size para redimensionar (ej. disk='scsi0', '+5G').
    """
    vmid = v.valid_vmid(vmid)
    guest_type = v.valid_guest_type(guest_type)
    args: List[str] = [_cli(guest_type), "set", str(vmid)]

    changed = False
    if cores is not None:
        args += ["--cores", str(v.valid_cores(cores))]
        changed = True
    if memory is not None:
        # qm usa --memory (MB); pct usa --memory (MB) también.
        args += ["--memory", str(v.valid_memory(memory))]
        changed = True
    if not changed and not disk:
        raise HTTPException(status_code=422, detail="No se especificó ningún recurso a modificar")

    rc, out, err = ssh_executor.run_command(node, args)
    _check_rc(rc, out, err, "set")

    # Redimensionado de disco (comando aparte: qm/pct resize)
    if disk and disk_size:
        disk_name = v.valid_name(disk, "disk")
        size = v.valid_disk_size(disk_size)
        rargs = [_cli(guest_type), "resize", str(vmid), disk_name, size]
        rrc, rout, rerr = ssh_executor.run_command(node, rargs)
        _check_rc(rrc, rout, rerr, "resize")
        out += "\n" + rout

    return out


# --- 3. Snapshots -----------------------------------------------------------

def create_snapshot(node, vmid, guest_type: str, name: str,
                    description: Optional[str] = None) -> str:
    vmid = v.valid_vmid(vmid)
    guest_type = v.valid_guest_type(guest_type)
    name = v.valid_name(name, "snapshot")
    args = [_cli(guest_type), "snapshot", str(vmid), name]
    if description:
        # description no entra en el comando como flag arbitrario: se valida nombre seguro.
        args += ["--description", v.valid_name(description.replace(" ", "_"), "description")]
    rc, out, err = ssh_executor.run_command(node, args)
    _check_rc(rc, out, err, "snapshot")
    return out


def list_snapshots(node, vmid, guest_type: str) -> List[dict]:
    vmid = v.valid_vmid(vmid)
    guest_type = v.valid_guest_type(guest_type)
    args = [_cli(guest_type), "listsnapshot", str(vmid)]
    rc, out, err = ssh_executor.run_command(node, args)
    _check_rc(rc, out, err, "listsnapshot")
    snaps = []
    for line in out.splitlines():
        # Formato tipo: " `-> snapname  2024-...  description"
        cleaned = line.replace("`->", "").replace("|", "").strip()
        if not cleaned:
            continue
        parts = cleaned.split()
        snap_name = parts[0]
        if snap_name in ("current",):
            continue
        snaps.append({"name": snap_name, "raw": cleaned})
    return snaps


def delete_snapshot(node, vmid, guest_type: str, name: str) -> str:
    vmid = v.valid_vmid(vmid)
    guest_type = v.valid_guest_type(guest_type)
    name = v.valid_name(name, "snapshot")
    args = [_cli(guest_type), "delsnapshot", str(vmid), name]
    rc, out, err = ssh_executor.run_command(node, args)
    _check_rc(rc, out, err, "delsnapshot")
    return out


def rollback_snapshot(node, vmid, guest_type: str, name: str) -> str:
    vmid = v.valid_vmid(vmid)
    guest_type = v.valid_guest_type(guest_type)
    name = v.valid_name(name, "snapshot")
    args = [_cli(guest_type), "rollback", str(vmid), name]
    rc, out, err = ssh_executor.run_command(node, args)
    _check_rc(rc, out, err, "rollback")
    return out


# --- Inventario -------------------------------------------------------------

def _parse_guest_list(out: str, guest_type: str) -> List[dict]:
    """Parsea la salida de `qm list` / `pct list`."""
    guests = []
    lines = [l for l in out.splitlines() if l.strip()]
    for line in lines[1:]:  # saltar cabecera
        parts = line.split()
        if not parts or not parts[0].isdigit():
            continue
        vmid = int(parts[0])
        if guest_type == "qemu":
            # VMID NAME STATUS MEM(MB) BOOTDISK(GB) PID
            name = parts[1] if len(parts) > 1 else None
            status = parts[2] if len(parts) > 2 else None
        else:
            # VMID STATUS LOCK NAME  (pct list: VMID Status Lock Name)
            status = parts[1] if len(parts) > 1 else None
            name = parts[-1] if len(parts) > 2 else None
        guests.append({"vmid": vmid, "name": name, "status": status, "guest_type": guest_type})
    return guests


def list_guests(node) -> List[dict]:
    """Lista VMs y contenedores del nodo (sin tocar la API)."""
    result: List[dict] = []
    rc, out, err = ssh_executor.run_command(node, ["qm", "list"])
    if rc == 0:
        result += _parse_guest_list(out, "qemu")
    rc2, out2, err2 = ssh_executor.run_command(node, ["pct", "list"])
    if rc2 == 0:
        result += _parse_guest_list(out2, "lxc")
    return result


# --- Ciclo de vida (encendido/apagado) -------------------------------------

def power_action(node, vmid, guest_type: str, action: str) -> str:
    """
    Ejecuta una acción de ciclo de vida sobre una VM (qemu) o contenedor (lxc).
    `action` se valida contra una allowlist; el comando es `qm/pct <action> <vmid>`.
    """
    vmid = v.valid_vmid(vmid)
    guest_type = v.valid_guest_type(guest_type)
    action = v.valid_power_action(action)
    args = [_cli(guest_type), action, str(vmid)]
    rc, out, err = ssh_executor.run_command(node, args)
    _check_rc(rc, out, err, action)
    return out.strip() or f"{action} ok"


def guest_status(node, vmid, guest_type: str) -> str:
    """Devuelve el estado actual del guest (`qm status` / `pct status`)."""
    vmid = v.valid_vmid(vmid)
    guest_type = v.valid_guest_type(guest_type)
    args = [_cli(guest_type), "status", str(vmid)]
    rc, out, err = ssh_executor.run_command(node, args)
    _check_rc(rc, out, err, "status")
    # Salida típica: "status: running"
    text = out.strip()
    if ":" in text:
        return text.split(":", 1)[1].strip()
    return text


def test_connection(node) -> str:
    """Verifica acceso SSH y disponibilidad de las herramientas Proxmox."""
    rc, out, err = ssh_executor.run_command(node, ["pveversion"])
    if rc != 0:
        raise HTTPException(status_code=502, detail=f"No se pudo verificar el nodo: {(err or out).strip()}")
    return out.strip()


# --- 2. Backups (vzdump) ----------------------------------------------------

def run_vzdump(node, vmid, storage: str, mode: str = "snapshot") -> tuple:
    """
    Ejecuta un backup de un guest. Devuelve (rc, stdout, stderr).
    No lanza excepción para permitir registrar el job aunque falle.
    """
    vmid = v.valid_vmid(vmid)
    storage = v.valid_storage(storage)
    mode = v.valid_backup_mode(mode)
    args = ["vzdump", str(vmid), "--storage", storage, "--mode", mode]
    return ssh_executor.run_command(node, args, timeout=3600)
