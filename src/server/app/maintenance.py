"""
Mantenimiento de datos: retención/purga de históricos.

La tabla `metrics` (y los resultados de checks) crecen de forma indefinida. Esta
purga elimina filas más antiguas que la ventana de retención configurada, para
evitar que la base de datos crezca sin control. Se ejecuta de forma programada
(APScheduler) y también puede dispararse manualmente desde un endpoint admin.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import delete
from sqlalchemy.orm import Session

from config.settings import METRICS_RETENTION_DAYS, CHECK_RESULTS_RETENTION_DAYS
from .database import engine
from .models import Metric, MonitoringCheckResult

logger = logging.getLogger(__name__)


def purge_old_data(metrics_days: int = None, checks_days: int = None) -> dict:
    """
    Borra métricas y resultados de checks más antiguos que la retención.
    Devuelve el número de filas eliminadas por tabla. days<=0 omite esa tabla.
    """
    metrics_days = METRICS_RETENTION_DAYS if metrics_days is None else metrics_days
    checks_days = CHECK_RESULTS_RETENTION_DAYS if checks_days is None else checks_days

    deleted = {"metrics": 0, "check_results": 0}
    with Session(engine) as sess:
        if metrics_days and metrics_days > 0:
            cutoff = datetime.utcnow() - timedelta(days=metrics_days)
            res = sess.execute(delete(Metric).where(Metric.ts < cutoff))
            deleted["metrics"] = res.rowcount or 0
        if checks_days and checks_days > 0:
            cutoff = datetime.utcnow() - timedelta(days=checks_days)
            res = sess.execute(delete(MonitoringCheckResult).where(MonitoringCheckResult.ts < cutoff))
            deleted["check_results"] = res.rowcount or 0
        sess.commit()
    logger.info("Purga de retención: %s", deleted)
    return deleted
