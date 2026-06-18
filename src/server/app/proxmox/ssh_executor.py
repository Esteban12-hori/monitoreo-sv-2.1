"""
Ejecución de comandos en nodos Proxmox vía SSH.

Este módulo es el ÚNICO punto del sistema que abre conexiones SSH y ejecuta
comandos remotos. Centralizarlo permite:
  - aplicar de forma uniforme el quoting seguro (shlex) y los timeouts,
  - verificar la host key (TOFU) y descifrar credenciales en un solo sitio,
  - mockearlo fácilmente en las pruebas (no hay Proxmox real en CI).

`paramiko` se importa de forma diferida para que el resto de la app sea
importable aunque la dependencia no esté instalada (p. ej. en tests que
mockean `run_command`).
"""
import shlex
import logging
from typing import List, Tuple

from ..security import decrypt_password

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60


class SSHCommandError(Exception):
    """Error de transporte/conexión SSH (no confundir con rc != 0)."""


def build_command(args: List[str], use_sudo: bool = False) -> str:
    """
    Construye la línea de comando final aplicando shlex.quote token a token.
    Nunca se interpola texto de usuario crudo: cada argumento se escapa.
    """
    if not args or not all(isinstance(a, str) for a in args):
        raise ValueError("args debe ser una lista de strings no vacía")
    quoted = " ".join(shlex.quote(a) for a in args)
    if use_sudo:
        quoted = "sudo -n " + quoted
    return quoted


def _load_pkey(secret: str):
    import io
    import paramiko
    for loader in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey):
        try:
            return loader.from_private_key(io.StringIO(secret))
        except Exception:
            continue
    raise SSHCommandError("No se pudo cargar la clave privada SSH")


def _connect(node):
    """Abre un cliente SSH a `node` verificando la host key (TOFU)."""
    import paramiko

    client = paramiko.SSHClient()
    # TOFU: si el nodo tiene huella registrada, exigimos que coincida;
    # si no, aceptamos y el llamador la persiste tras el primer contacto.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    secret = decrypt_password(node.secret_encrypted)
    connect_kwargs = dict(
        hostname=node.hostname,
        port=node.ssh_port or 22,
        username=node.ssh_user or "root",
        timeout=DEFAULT_TIMEOUT,
        allow_agent=False,
        look_for_keys=False,
    )
    if node.auth_type == "key":
        connect_kwargs["pkey"] = _load_pkey(secret)
    else:
        connect_kwargs["password"] = secret

    try:
        client.connect(**connect_kwargs)
    except Exception as e:
        raise SSHCommandError(f"Fallo de conexión SSH a {node.hostname}: {e}")

    # Verificación de host key (TOFU)
    transport = client.get_transport()
    server_key = transport.get_remote_server_key() if transport else None
    fingerprint = None
    if server_key is not None:
        import hashlib
        import base64
        digest = hashlib.sha256(server_key.asbytes()).digest()
        fingerprint = "SHA256:" + base64.b64encode(digest).decode().rstrip("=")
        expected = getattr(node, "host_key_fingerprint", None)
        if expected and expected != fingerprint:
            client.close()
            raise SSHCommandError(
                "La huella de la host key cambió: posible MITM, conexión abortada"
            )

    return client, fingerprint


def get_host_fingerprint(node) -> str:
    """Conecta y devuelve la huella SHA256 de la host key (para registro TOFU)."""
    client, fingerprint = _connect(node)
    try:
        return fingerprint
    finally:
        client.close()


def run_command(node, args: List[str], timeout: int = DEFAULT_TIMEOUT) -> Tuple[int, str, str]:
    """
    Ejecuta `args` (lista de strings ya validados) en `node` por SSH.

    Devuelve (return_code, stdout, stderr). Esta función es el punto de
    integración mockeado en las pruebas.
    """
    command = build_command(args, use_sudo=getattr(node, "use_sudo", False))
    client, _ = _connect(node)
    try:
        _stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        rc = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        logger.info("SSH %s@%s rc=%s cmd=%s", node.ssh_user, node.hostname, rc, args[0:2])
        return rc, out, err
    finally:
        client.close()
