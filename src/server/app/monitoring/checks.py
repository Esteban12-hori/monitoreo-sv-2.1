"""
Ejecutores de checks agentless (server-side) y runner programado.

A diferencia de los plugins del agente (con objetivos fijos), estos checks se
configuran desde la UI y los ejecuta el propio backend, lo que permite
monitorizar dispositivos/endpoints sin instalar nada en ellos (paridad básica
con el monitoreo agentless de Zabbix).

Cada ejecutor devuelve un dict: {"status": up|down, "latency_ms": float|None,
"message": str}. Las primitivas de red son fácilmente mockeables en tests.
"""
import time
import socket
import logging
import platform
import subprocess
import re
from datetime import datetime

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import engine
from ..models import MonitoringCheck, MonitoringCheckResult

logger = logging.getLogger(__name__)

VALID_CHECK_TYPES = ("http", "tcp", "icmp")


def run_http_check(target: str, timeout: int = 10, expected_status: int = None) -> dict:
    start = time.time()
    try:
        resp = requests.get(target, timeout=timeout, allow_redirects=True)
        latency = round((time.time() - start) * 1000, 2)
        ok = (resp.status_code == expected_status) if expected_status else (resp.status_code < 400)
        return {"status": "up" if ok else "down", "latency_ms": latency,
                "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "down", "latency_ms": None, "message": str(e)[:200]}


def run_tcp_check(host: str, port: int, timeout: int = 10) -> dict:
    start = time.time()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            latency = round((time.time() - start) * 1000, 2)
            return {"status": "up", "latency_ms": latency, "message": f"TCP {host}:{port} abierto"}
    except Exception as e:
        return {"status": "down", "latency_ms": None, "message": str(e)[:200]}


_ICMP_RE = re.compile(r"time[=<]([\d\.]+)\s*ms", re.IGNORECASE)


def run_icmp_check(host: str, timeout: int = 10) -> dict:
    param = "-n" if platform.system().lower() == "windows" else "-c"
    cmd = ["ping", param, "1", host]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=timeout + 2)
        m = _ICMP_RE.search(out)
        latency = float(m.group(1)) if m else None
        return {"status": "up", "latency_ms": latency, "message": "ICMP responde"}
    except Exception as e:
        return {"status": "down", "latency_ms": None, "message": str(e)[:200]}


def run_check(check: MonitoringCheck) -> dict:
    """Despacha a la primitiva correcta según el tipo de check."""
    t = check.timeout_seconds or 10
    if check.check_type == "http":
        return run_http_check(check.target, t, check.expected_status)
    if check.check_type == "tcp":
        port = check.port or (int(check.target.split(":")[1]) if ":" in check.target else None)
        host = check.target.split(":")[0]
        if not port:
            return {"status": "unknown", "latency_ms": None, "message": "Puerto TCP no especificado"}
        return run_tcp_check(host, port, t)
    if check.check_type == "icmp":
        return run_icmp_check(check.target, t)
    return {"status": "unknown", "latency_ms": None, "message": "Tipo de check no soportado"}


def execute_and_store(check_id: int) -> dict:
    """Ejecuta un check, guarda el resultado e historial. Devuelve el resultado."""
    with Session(engine) as sess:
        check = sess.get(MonitoringCheck, check_id)
        if not check or not check.enabled:
            return {}
        result = run_check(check)
        now = datetime.utcnow()
        check.last_status = result["status"]
        check.last_latency_ms = result.get("latency_ms")
        check.last_message = result.get("message")
        check.last_checked_at = now
        sess.add(MonitoringCheckResult(
            check_id=check.id, status=result["status"],
            latency_ms=result.get("latency_ms"), message=result.get("message"),
        ))
        sess.commit()
        return result


def run_all_due_checks() -> int:
    """
    Ejecuta los checks habilitados que toca correr según su intervalo.
    Pensado para invocarse periódicamente desde el scheduler.
    """
    ran = 0
    with Session(engine) as sess:
        checks = sess.execute(select(MonitoringCheck).where(MonitoringCheck.enabled == True)).scalars().all()  # noqa: E712
        due_ids = []
        now = datetime.utcnow()
        for c in checks:
            if c.last_checked_at is None:
                due_ids.append(c.id)
            else:
                last = c.last_checked_at
                if last.tzinfo is not None:
                    last = last.replace(tzinfo=None)
                if (now - last).total_seconds() >= (c.interval_seconds or 60):
                    due_ids.append(c.id)
    for cid in due_ids:
        try:
            execute_and_store(cid)
            ran += 1
        except Exception as e:
            logger.warning("Check %s falló: %s", cid, e)
    return ran
