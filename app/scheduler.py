from apscheduler.schedulers.asyncio import AsyncIOScheduler

import logging

from app import automation, import_lists as import_lists_service, library_match, library_scan, plex_scan, remote_access, settings as settings_module
from app.db import SessionLocal

scheduler = AsyncIOScheduler()
JOB_ID = "automation_cycle"
PLEX_JOB_ID = "plex_scan"
IMPORT_LISTS_JOB_ID = "import_lists_sync"
LIBRARY_SCAN_JOB_ID = "library_scan"
REMOTE_ACCESS_JOB_ID = "remote_access_check"
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


async def _import_lists_job() -> None:
    db = SessionLocal()
    try:
        await import_lists_service.sync_all(db)
    except Exception:
        log.warning("scheduled import list sync failed", exc_info=True)
    finally:
        db.close()


async def _library_scan_job() -> None:
    """M50a/M50b: reconcile media_files with what is on disk, then try to place the files the
    scan could not identify against TMDB."""
    db = SessionLocal()
    try:
        library_scan.scan(db)
        db.commit()
        await library_match.match_movies(db)
        await library_match.match_episodes(db)
        db.commit()
    except Exception:
        db.rollback()
        log.warning("scheduled library scan failed", exc_info=True)
    finally:
        db.close()


async def _remote_access_job():
    """Re-check the remote access guard and the router mapping, then test NAT loopback once mapped (M36)."""
    from app import remote_access, setup_state
    db = SessionLocal()
    try:
        s = settings_module.effective(db)
        remote_access.apply(s, setup_state.is_complete(db))
        if remote_access.status()["state"] == "mapped":
            await remote_access.check_loopback(s)
    finally:
        db.close()


def start() -> None:
    db = SessionLocal()
    try:
        s = settings_module.effective(db)
        interval, plex_minutes, import_list_minutes = s.automation_interval_seconds, s.plex_scan_interval_minutes, s.import_list_interval_minutes
        library_minutes = s.library_scan_interval_minutes
    finally:
        db.close()
    scheduler.add_job(_job, "interval", seconds=interval, id=JOB_ID)
    scheduler.add_job(_plex_job, "interval", minutes=plex_minutes, id=PLEX_JOB_ID)
    scheduler.add_job(_import_lists_job, "interval", minutes=import_list_minutes, id=IMPORT_LISTS_JOB_ID)
    scheduler.add_job(_library_scan_job, "interval", minutes=library_minutes, id=LIBRARY_SCAN_JOB_ID)
    scheduler.add_job(_remote_access_job, "interval", minutes=10, id=REMOTE_ACCESS_JOB_ID)
    scheduler.start()


def reschedule(seconds: int) -> None:
    """Apply a new automation interval immediately, without restarting the app."""
    scheduler.reschedule_job(JOB_ID, trigger="interval", seconds=seconds)


def reschedule_plex(minutes: int) -> None:
    scheduler.reschedule_job(PLEX_JOB_ID, trigger="interval", minutes=minutes)


def reschedule_import_lists(minutes: int) -> None:
    scheduler.reschedule_job(IMPORT_LISTS_JOB_ID, trigger="interval", minutes=minutes)


def reschedule_library_scan(minutes: int) -> None:
    scheduler.reschedule_job(LIBRARY_SCAN_JOB_ID, trigger="interval", minutes=minutes)


def stop() -> None:
    scheduler.shutdown(wait=False)
