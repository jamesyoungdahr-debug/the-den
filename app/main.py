from fastapi import FastAPI
from sqlalchemy import text

from app.db import SessionLocal, engine
from app.models import QualityProfile
from app.routers import downloads, indexers, movies, search, ui

app = FastAPI(title="The Den")
app.include_router(indexers.router)
app.include_router(search.router)
app.include_router(movies.router)
app.include_router(downloads.router)
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


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
