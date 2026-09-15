from apscheduler.schedulers.asyncio import AsyncIOScheduler

import asyncio
import logging

from app import automation, ffmpeg_jobs, import_lists as import_lists_service, library_match, library_scan, plex_scan, remote_access, settings as settings_module, transcode
from app.db import SessionLocal

scheduler = AsyncIOScheduler()
JOB_ID = "automation_cycle"
PLEX_JOB_ID = "plex_scan"
IMPORT_LISTS_JOB_ID = "import_lists_sync"
LIBRARY_SCAN_JOB_ID = "library_scan"
REMOTE_ACCESS_JOB_ID = "remote_access_check"
MEDIA_HOUSEKEEPING_JOB_ID = "media_housekeeping"
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


def _scan_in_thread() -> dict:
    """The filesystem walk is blocking, so it gets its own session and its own thread."""
    db = SessionLocal()
    try:
        result = library_scan.scan(db)
        db.commit()
        return result
    finally:
        db.close()


async def _match_in_session() -> int:
    """Both matchers, on the event loop because they await TMDB. Returns how many files were placed."""
    db = SessionLocal()
    try:
        movies = await library_match.match_movies(db)
        episodes = await library_match.match_episodes(db)
        db.commit()
        return movies["matched"] + episodes["matched"]
    finally:
        db.close()


async def run_library_scan() -> dict:
    """M50a/M50b: one scan and both matchers, publishing progress for the Settings page to poll.
    The walk runs in a worker thread so a big library cannot block the event loop. Shared by the
    scheduled job and the Settings "Scan now" button."""
    try:
        result = await asyncio.to_thread(_scan_in_thread)
        library_scan.update_progress(
            running=True, phase="matching", seen=result["seen"], added=result["added"],
            unmatched=result["unmatched"], missing=result["missing"],
        )
        placed = await _match_in_session()
    except Exception as exc:
        log.warning("library scan failed", exc_info=True)
        library_scan.finish_progress("failed", error=str(exc))
        raise
    library_scan.finish_progress("done", placed=placed)
    return result


async def _library_scan_job() -> None:
    """The scheduled form of run_library_scan; it has already logged and marked the failure."""
    try:
        await run_library_scan()
    except Exception:
        pass


async def _media_housekeeping_job() -> None:
    """M50b/P2: kill abandoned ffmpeg jobs and keep the converted-file cache under its ceiling.
    A timer rather than a request, so a request never waits on somebody else's cleanup."""
    try:
        killed = ffmpeg_jobs.reap()
        pruned = transcode.prune_cache()
        if killed or pruned["removed"]:
            log.info("housekeeping: reaped %d job(s), dropped %d cached file(s)", killed, pruned["removed"])
    except Exception:
        log.warning("media housekeeping failed", exc_info=True)


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
    scheduler.add_job(_media_housekeeping_job, "interval", minutes=5, id=MEDIA_HOUSEKEEPING_JOB_ID)
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
