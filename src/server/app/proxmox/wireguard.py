"""
Túnel WireGuard cifrado entre nodos y migración de cargas de trabajo.

La migración no usa la API de Proxmox: se realiza por completo con CLI nativos
sobre un túnel WireGuard (cifrado ChaCha20-Poly1305, lo que garantiza
confidencialidad e integridad del tráfico):

  1) `vzdump` del guest en el nodo origen,
  2) transferencia del archivo al nodo destino a través de la IP del túnel
     WireGuard (rsync/ssh nodo→nodo),
  3) `qmrestore` / `pct restore` en el nodo destino.

Las claves WireGuard (Curve25519) se generan con `cryptography` (no requiere el
binario `wg` en el backend) y las privadas se almacenan cifradas con Fernet.
"""
import os
import re
import shlex
import base64
import logging
from typing import Tuple

from fastapi import HTTPException
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization

from . import ssh_executor
from . import validators as v
from ..security import encrypt_password, decrypt_password

logger = logging.getLogger(__name__)

# Subred del túnel (cada link usa una /30). Configurable por entorno.
TUNNEL_NET_PREFIX = os.getenv("WG_TUNNEL_PREFIX", "10.99.99")
DEFAULT_LISTEN_PORT = int(os.getenv("WG_LISTEN_PORT", "51830"))
DUMP_DIR = "/var/lib/vz/dump"

_ARCHIVE_RE = re.compile(r"creating (?:vzdump )?archive '([^']+)'")


def generate_wg_keypair() -> Tuple[str, str]:
    """Devuelve (private_key_b64, public_key_b64) válidos para WireGuard."""
    priv = X25519PrivateKey.generate()
    priv_raw = priv.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    pub_raw = priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return base64.b64encode(priv_raw).decode(), base64.b64encode(pub_raw).decode()


def _wg_conf(iface: str, private_key: str, listen_port: int, local_ip: str,
             peer_pubkey: str, peer_endpoint_host: str, peer_endpoint_port: int,
             peer_ip: str) -> str:
    """Genera el contenido de /etc/wireguard/<iface>.conf con valores validados."""
    return (
        "[Interface]\n"
        f"PrivateKey = {private_key}\n"
        f"Address = {local_ip}/30\n"
        f"ListenPort = {listen_port}\n\n"
        "[Peer]\n"
        f"PublicKey = {peer_pubkey}\n"
        f"AllowedIPs = {peer_ip}/32\n"
        f"Endpoint = {peer_endpoint_host}:{peer_endpoint_port}\n"
        "PersistentKeepalive = 25\n"
    )


def _apply_conf(node, iface: str, conf: str):
    """Escribe la config (umask 077) y levanta la interfaz vía wg-quick."""
    import shlex
    conf_q = shlex.quote(conf)
    script = (
        "umask 077; mkdir -p /etc/wireguard; "
        f"printf '%s' {conf_q} > /etc/wireguard/{iface}.conf; "
        f"wg-quick down {iface} 2>/dev/null; wg-quick up {iface}"
    )
    rc, out, err = ssh_executor.run_command(node, ["sh", "-c", script])
    if rc != 0:
        raise HTTPException(status_code=502, detail=f"No se pudo levantar el túnel en {node.name}: {(err or out).strip()}")
    return out


def create_link(link, source_node, target_node) -> dict:
    """
    Establece el túnel WireGuard entre source_node y target_node.
    Rellena claves/IPs en `link` (las privadas cifradas) y configura ambos extremos.
    Devuelve metadatos del túnel.
    """
    iface = v.valid_name(link.wg_interface or "wg-mig0", "wg_interface")
    listen_port = v.valid_port(link.listen_port or DEFAULT_LISTEN_PORT, "listen_port")
    src_host = v.valid_hostname(source_node.hostname)
    dst_host = v.valid_hostname(target_node.hostname)

    src_priv, src_pub = generate_wg_keypair()
    dst_priv, dst_pub = generate_wg_keypair()

    src_ip = v.valid_tunnel_ip(f"{TUNNEL_NET_PREFIX}.1")
    dst_ip = v.valid_tunnel_ip(f"{TUNNEL_NET_PREFIX}.2")

    # Configurar ambos extremos
    src_conf = _wg_conf(iface, src_priv, listen_port, src_ip, dst_pub, dst_host, listen_port, dst_ip)
    dst_conf = _wg_conf(iface, dst_priv, listen_port, dst_ip, src_pub, src_host, listen_port, src_ip)
    _apply_conf(source_node, iface, src_conf)
    _apply_conf(target_node, iface, dst_conf)

    # Persistir en el modelo (privadas cifradas)
    link.wg_interface = iface
    link.listen_port = listen_port
    link.source_wg_pubkey = src_pub
    link.target_wg_pubkey = dst_pub
    link.source_wg_privkey_encrypted = encrypt_password(src_priv)
    link.target_wg_privkey_encrypted = encrypt_password(dst_priv)
    link.source_tunnel_ip = src_ip
    link.target_tunnel_ip = dst_ip
    link.status = "up"

    return {"interface": iface, "source_ip": src_ip, "target_ip": dst_ip, "status": "up"}


def teardown_link(link, source_node, target_node):
    iface = v.valid_name(link.wg_interface or "wg-mig0", "wg_interface")
    for node in (source_node, target_node):
        try:
            ssh_executor.run_command(node, ["sh", "-c", f"wg-quick down {iface} 2>/dev/null; rm -f /etc/wireguard/{iface}.conf"])
        except Exception as e:
            logger.warning("Error bajando túnel en %s: %s", getattr(node, "name", "?"), e)
    link.status = "down"


def migrate_guest(link, source_node, target_node, vmid, guest_type: str,
                  storage: str, online: bool = False) -> str:
    """
    Migra un guest del nodo origen al destino a través del túnel WireGuard.
    Estrategia API-free: vzdump -> transferencia por el túnel -> restore.
    """
    vmid = v.valid_vmid(vmid)
    guest_type = v.valid_guest_type(guest_type)
    storage = v.valid_storage(storage)
    if link.status != "up" or not link.target_tunnel_ip:
        raise HTTPException(status_code=409, detail="El túnel WireGuard no está activo")
    target_ip = v.valid_tunnel_ip(link.target_tunnel_ip)

    log = []

    # 1) Backup en origen
    rc, out, err = ssh_executor.run_command(
        source_node, ["vzdump", str(vmid), "--storage", storage, "--mode", "snapshot"], timeout=3600
    )
    log.append(out)
    if rc != 0:
        raise HTTPException(status_code=502, detail=f"vzdump falló: {(err or out).strip()}")

    match = _ARCHIVE_RE.search(out)
    if not match:
        raise HTTPException(status_code=502, detail="No se pudo determinar el archivo de backup generado")
    archive = match.group(1)
    # El path proviene de la salida de Proxmox; validamos que sea un path de dump esperado.
    if not archive.startswith(DUMP_DIR) or "'" in archive or " " in archive:
        raise HTTPException(status_code=502, detail="Ruta de archivo de backup inesperada")

    # 2) Transferencia nodo→nodo POR EL TÚNEL (IP WireGuard cifrada)
    # Defensa en profundidad: el destino se cita aunque ssh_user ya se valida con
    # allowlist al crear el nodo (revalidación aquí por si proviene de datos antiguos).
    target_user = v.valid_name(target_node.ssh_user or "root", "ssh_user")
    transfer = (
        f"rsync -e 'ssh -o StrictHostKeyChecking=accept-new' -av "
        f"{shlex.quote(archive)} {shlex.quote(f'{target_user}@{target_ip}:{DUMP_DIR}/')}"
    )
    rc, out, err = ssh_executor.run_command(source_node, ["sh", "-c", transfer], timeout=3600)
    log.append(out)
    if rc != 0:
        raise HTTPException(status_code=502, detail=f"Transferencia por el túnel falló: {(err or out).strip()}")

    # 3) Restore en destino
    archive_name = archive.split("/")[-1]
    target_archive = f"{DUMP_DIR}/{archive_name}"
    if guest_type == "qemu":
        restore = ["qmrestore", target_archive, str(vmid), "--storage", storage]
    else:
        restore = ["pct", "restore", str(vmid), target_archive, "--storage", storage]
    rc, out, err = ssh_executor.run_command(target_node, restore, timeout=3600)
    log.append(out)
    if rc != 0:
        raise HTTPException(status_code=502, detail=f"Restore en destino falló: {(err or out).strip()}")

    return "\n".join(l for l in log if l)
