"""
Autodetección de guests que ejecutan bases de datos.

Reutiliza los datos que el agente ya reporta (servicios a la escucha y procesos
top, almacenados en la tabla `metrics`) para decidir si el servidor monitoreado
asociado a un guest Proxmox corre una base de datos. Marca `ProxmoxGuest.is_db`
en consecuencia, lo que alimenta los backups con `only_db=True`.
"""
import json
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Metric, ProxmoxGuest

logger = logging.getLogger(__name__)

# Firmas configurables: nombres de proceso/servicio y puertos en escucha.
DB_NAME_SIGNATURES = (
    "postgres", "postmaster", "mysqld", "mysql", "mariadb", "mongod", "mongo",
    "redis-server", "redis", "sqlservr", "oracle", "db2", "cockroach", "couchdb",
)
DB_PORT_SIGNATURES = {5432, 3306, 33060, 27017, 6379, 1433, 1521, 5984, 26257, 50000}


def _latest_metric(sess: Session, server_id: str):
    return sess.execute(
        select(Metric).where(Metric.server_id == server_id).order_by(Metric.id.desc()).limit(1)
    ).scalar_one_or_none()


def server_runs_db(sess: Session, server_id: str) -> bool:
    """True si el último métrico del servidor muestra una base de datos."""
    if not server_id:
        return False
    m = _latest_metric(sess, server_id)
    if not m:
        return False

    try:
        services = json.loads(m.services or "[]")
    except Exception:
        services = []
    try:
        processes = json.loads(m.processes or "[]")
    except Exception:
        processes = []

    for s in services:
        name = str(s.get("name", "")).lower()
        port = s.get("port")
        if any(sig in name for sig in DB_NAME_SIGNATURES):
            return True
        try:
            if port is not None and int(port) in DB_PORT_SIGNATURES:
                return True
        except (TypeError, ValueError):
            pass

    for p in processes:
        name = str(p.get("name", "")).lower()
        if any(sig in name for sig in DB_NAME_SIGNATURES):
            return True

    return False


def detect_db_guests(sess: Session) -> int:
    """
    Recorre los guests con servidor monitoreado vinculado y actualiza is_db.
    Devuelve el número de guests marcados como BD.
    """
    guests = sess.execute(
        select(ProxmoxGuest).where(ProxmoxGuest.linked_server_id.is_not(None))
    ).scalars().all()

    marked = 0
    for g in guests:
        is_db = server_runs_db(sess, g.linked_server_id)
        if g.is_db != is_db:
            g.is_db = is_db
        if is_db:
            marked += 1
    sess.commit()
    logger.info("Autodetección BD: %s guests marcados como base de datos", marked)
    return marked
