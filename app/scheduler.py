from apscheduler.schedulers.asyncio import AsyncIOScheduler

import logging

from app import automation, plex_scan, settings as settings_module
from app.db import SessionLocal

scheduler = AsyncIOScheduler()
JOB_ID = "automation_cycle"
PLEX_JOB_ID = "plex_scan"
log = logging.getLogger(__name__)


async def _job() -> None:
    db = SessionLocal()
    try:
        await automation.run_cycle(db)
    finally:
        db.close()


async def _plex_job() -> None:
    db = SessionLocal()
    try:
        await plex_scan.scan(db)
        from app import requests_service  # local: requests_service imports plex_scan
        await requests_service.mark_available(db)
    except plex_scan.NotConfigured:
        pass  # nothing to scan until an admin connects Plex and picks a server
    except Exception:
        log.warning("scheduled Plex scan failed", exc_info=True)
    finally:
        db.close()


def start() -> None:
    db = SessionLocal()
    try:
        s = settings_module.effective(db)
        interval, plex_minutes = s.automation_interval_seconds, s.plex_scan_interval_minutes
    finally:
        db.close()
    scheduler.add_job(_job, "interval", seconds=interval, id=JOB_ID)
    scheduler.add_job(_plex_job, "interval", minutes=plex_minutes, id=PLEX_JOB_ID)
    scheduler.start()


def reschedule(seconds: int) -> None:
    """Apply a new automation interval immediately, without restarting the app."""
    scheduler.reschedule_job(JOB_ID, trigger="interval", seconds=seconds)


def reschedule_plex(minutes: int) -> None:
    scheduler.reschedule_job(PLEX_JOB_ID, trigger="interval", minutes=minutes)


def stop() -> None:
    scheduler.shutdown(wait=False)
