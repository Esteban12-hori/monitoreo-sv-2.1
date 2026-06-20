"""
Programación de backups con APScheduler.

`init_scheduler()` se invoca en el startup de FastAPI: arranca el scheduler y
registra un job cron por cada `BackupSchedule` habilitado. Cada disparo ejecuta
`run_backup_schedule`, que resuelve los guests objetivo (todos o solo los
detectados como BD) y ejecuta `vzdump` registrando un `BackupJob` por guest.

APScheduler se importa de forma diferida para no romper la importación del
módulo cuando la dependencia no está instalada (p. ej. en pruebas que ejercen
`run_backup_schedule` directamente).
"""
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import engine
from ..models import BackupSchedule, BackupJob, ProxmoxGuest, ProxmoxNode
from . import service
from . import dbdetect

logger = logging.getLogger(__name__)

_scheduler = None


def _resolve_targets(sess: Session, schedule: BackupSchedule):
    """Devuelve la lista de (node, guest) objetivo del schedule."""
    q = select(ProxmoxGuest)
    if schedule.node_id:
        q = q.where(ProxmoxGuest.node_id == schedule.node_id)
    if schedule.only_db:
        q = q.where(ProxmoxGuest.is_db == True)  # noqa: E712
    guests = sess.execute(q).scalars().all()
    targets = []
    for g in guests:
        node = sess.get(ProxmoxNode, g.node_id)
        if node:
            targets.append((node, g))
    return targets


def run_backup_schedule(schedule_id: int) -> int:
    """
    Ejecuta el backup de todos los guests objetivo del schedule.
    Devuelve el número de jobs ejecutados. Crea un BackupJob por guest.
    """
    with Session(engine) as sess:
        schedule = sess.get(BackupSchedule, schedule_id)
        if not schedule or not schedule.enabled:
            return 0

        # Refrescar autodetección de BD antes de filtrar.
        if schedule.only_db:
            try:
                dbdetect.detect_db_guests(sess)
            except Exception as e:
                logger.warning("Autodetección BD falló: %s", e)

        targets = _resolve_targets(sess, schedule)
        count = 0
        for node, guest in targets:
            job = BackupJob(
                schedule_id=schedule.id, node_id=node.id, vmid=guest.vmid,
                storage=schedule.storage, status="running",
            )
            sess.add(job)
            sess.commit()
            sess.refresh(job)
            try:
                rc, out, err = service.run_vzdump(node, guest.vmid, schedule.storage, schedule.mode)
                job.status = "ok" if rc == 0 else "error"
                job.output_log = (out or "") + (("\n" + err) if err else "")
            except Exception as e:
                job.status = "error"
                job.output_log = str(e)
            job.finished_at = datetime.utcnow()
            sess.commit()
            count += 1
        logger.info("Backup schedule %s ejecutado: %s jobs", schedule_id, count)
        return count


def _add_job(scheduler, schedule: BackupSchedule):
    from apscheduler.triggers.cron import CronTrigger
    trigger = CronTrigger.from_crontab(schedule.cron_expr)
    scheduler.add_job(
        run_backup_schedule, trigger=trigger, args=[schedule.id],
        id=f"backup_schedule_{schedule.id}", replace_existing=True,
    )


def add_schedule_job(schedule: BackupSchedule):
    if _scheduler is None or not schedule.enabled:
        return
    try:
        _add_job(_scheduler, schedule)
    except Exception as e:
        logger.error("No se pudo registrar el schedule %s: %s", schedule.id, e)


def remove_schedule_job(schedule_id: int):
    if _scheduler is None:
        return
    try:
        _scheduler.remove_job(f"backup_schedule_{schedule_id}")
    except Exception:
        pass


def init_scheduler():
    """Arranca APScheduler y registra los schedules habilitados."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except Exception as e:
        logger.warning("APScheduler no disponible, backups programados deshabilitados: %s", e)
        return None

    _scheduler = AsyncIOScheduler()
    with Session(engine) as sess:
        schedules = sess.execute(
            select(BackupSchedule).where(BackupSchedule.enabled == True)  # noqa: E712
        ).scalars().all()
        for sch in schedules:
            try:
                _add_job(_scheduler, sch)
            except Exception as e:
                logger.error("Schedule %s inválido: %s", sch.id, e)

    # Job recurrente: ejecutar los checks agentless que toquen según su intervalo.
    try:
        from ..monitoring.checks import run_all_due_checks
        _scheduler.add_job(run_all_due_checks, "interval", seconds=30,
                           id="agentless_checks", replace_existing=True)
    except Exception as e:
        logger.error("No se pudo registrar el runner de checks: %s", e)

    # Job diario: purga de retención de históricos.
    try:
        from ..maintenance import purge_old_data
        _scheduler.add_job(purge_old_data, "cron", hour=4, minute=0,
                           id="data_retention", replace_existing=True)
    except Exception as e:
        logger.error("No se pudo registrar la purga de retención: %s", e)

    _scheduler.start()
    logger.info("Scheduler iniciado (%d backups + checks + retención)", len(schedules))
    return _scheduler


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
