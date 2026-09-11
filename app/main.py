from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import automation, scheduler
from app import settings as settings_module
from app.db import SessionLocal, engine as db_engine
from app.deps import get_db
from app.models import QualityProfile
from app.routers import api_settings, downloads, indexers, movies, search, series, torrents, ui
from app.torrent import engine as torrent_engine

app = FastAPI(title="The Den")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(indexers.router)
app.include_router(search.router)
app.include_router(movies.router)
app.include_router(series.router)
app.include_router(downloads.router)
app.include_router(torrents.router)
app.include_router(api_settings.router)
app.include_router(ui.router)


@app.on_event("startup")
def seed_default_quality_profile():
    db = SessionLocal()
    try:
        if not db.query(QualityProfile).first():
            db.add(QualityProfile(name="Default", allowed_qualities="1080p,720p,480p", cutoff="1080p"))
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
async def start_torrent_engine():
    # Before the scheduler: its first cycle polls the engine for in-flight downloads.
    db = SessionLocal()
    try:
        cfg = settings_module.effective(db).engine_config()
    finally:
        db.close()
    torrent_engine.start(cfg)


@app.on_event("startup")
def start_scheduler():
    scheduler.start()


@app.on_event("shutdown")
def stop_scheduler():
    scheduler.stop()


@app.on_event("shutdown")
async def stop_torrent_engine():
    await torrent_engine.stop()


@app.post("/automation/run-now")
async def run_automation_now(db: Session = Depends(get_db)):
    await automation.run_cycle(db)
    return {"status": "ok"}


@app.get("/health")
def health():
    with db_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "torrent_engine": torrent_engine.info()}
