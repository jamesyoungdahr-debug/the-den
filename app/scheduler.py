from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app import automation, config
from app.db import SessionLocal

scheduler = AsyncIOScheduler()


async def _job() -> None:
    db = SessionLocal()
    try:
        await automation.run_cycle(db)
    finally:
        db.close()


def start() -> None:
    scheduler.add_job(_job, "interval", seconds=config.AUTOMATION_INTERVAL_SECONDS, id="automation_cycle")
    scheduler.start()


def stop() -> None:
    scheduler.shutdown(wait=False)
