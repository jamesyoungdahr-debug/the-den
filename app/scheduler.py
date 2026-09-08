from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app import automation, settings as settings_module
from app.db import SessionLocal

scheduler = AsyncIOScheduler()
JOB_ID = "automation_cycle"


async def _job() -> None:
    db = SessionLocal()
    try:
        await automation.run_cycle(db)
    finally:
        db.close()


def start() -> None:
    db = SessionLocal()
    try:
        interval = settings_module.effective(db).automation_interval_seconds
    finally:
        db.close()
    scheduler.add_job(_job, "interval", seconds=interval, id=JOB_ID)
    scheduler.start()


def reschedule(seconds: int) -> None:
    """Apply a new automation interval immediately, without restarting the app."""
    scheduler.reschedule_job(JOB_ID, trigger="interval", seconds=seconds)


def stop() -> None:
    scheduler.shutdown(wait=False)
