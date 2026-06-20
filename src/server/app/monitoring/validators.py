"""
Validación de objetivos de checks agentless.

Aunque los checks solo los crea un administrador, el `target` termina formando
parte de invocaciones a `ping`/`socket`/`requests`, por lo que debe validarse:

  - ICMP/TCP: el host debe ser un hostname o IP con forma válida. Se rechaza
    cualquier valor que empiece por '-' para evitar que `ping` lo interprete
    como una opción (argument injection, p. ej. `-f` flood).
  - HTTP: el target debe ser una URL http(s) bien formada.

Cualquier valor que no encaje produce un HTTP 422 antes de ejecutar nada.
"""
import ipaddress
import re
from urllib.parse import urlparse

from fastapi import HTTPException

# Hostname (RFC 1123, labels separados por puntos) sin metacaracteres ni guion inicial.
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)


def _fail(detail: str):
    raise HTTPException(status_code=422, detail=detail)


def valid_host(value: str, field: str = "host") -> str:
    """Acepta IPv4/IPv6 o un hostname válido. Rechaza guion inicial y vacíos."""
    if not isinstance(value, str):
        _fail(f"{field} inválido")
    value = value.strip()
    if not value or value.startswith("-"):
        _fail(f"{field} inválido")
    # ¿Es una IP literal? (ipaddress acepta v4 y v6)
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    if not _HOSTNAME_RE.match(value):
        _fail(f"{field} inválido: debe ser una IP o hostname válido")
    return value


def valid_http_target(value: str) -> str:
    """El target de un check HTTP debe ser una URL http(s) con host."""
    if not isinstance(value, str):
        _fail("target inválido")
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        _fail("target HTTP inválido: usa una URL http(s) completa")
    # El host de la URL también debe tener forma válida.
    valid_host(parsed.hostname, "host de la URL")
    return value


def validate_check_target(check_type: str, target: str, port=None) -> None:
    """
    Valida `target`/`port` según el tipo de check. No devuelve nada; lanza 422.
    Para TCP, el host puede venir como 'host:port' o con `port` aparte.
    """
    if check_type == "http":
        valid_http_target(target)
    elif check_type == "tcp":
        host = (target or "").split(":")[0]
        valid_host(host, "host TCP")
        # El puerto puede venir embebido (host:port) o en el campo `port`.
        embedded = None
        if ":" in (target or ""):
            try:
                embedded = int(target.split(":", 1)[1])
            except (ValueError, IndexError):
                _fail("puerto TCP inválido en el target")
        effective_port = port if port is not None else embedded
        if effective_port is None:
            _fail("un check TCP requiere puerto (campo 'port' o 'host:port')")
        if not (1 <= int(effective_port) <= 65535):
            _fail("puerto TCP fuera de rango (1-65535)")
    elif check_type == "icmp":
        valid_host(target, "host ICMP")
    else:
        _fail("tipo de check no soportado")
