from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import tvmaze
from app.candidates import scored_candidates
from app.deps import get_db
from app.grabber import grab_episode as do_grab_episode
from app.models import Episode, QualityProfile, Series
from app.schemas import DownloadRecordOut, EpisodeOut, GrabRequest, ScoredReleaseOut, SeriesCreate, SeriesOut

router = APIRouter(tags=["series"])


@router.get("/series/search-tvmaze")
async def search_tvmaze(q: str):
    return await tvmaze.search_tv(q)


@router.get("/series", response_model=list[SeriesOut])
def list_series(db: Session = Depends(get_db)):
    return db.query(Series).all()


@router.post("/series", response_model=SeriesOut, status_code=201)
async def add_series(payload: SeriesCreate, db: Session = Depends(get_db)):
    if db.query(Series).filter(Series.tvmaze_id == payload.tvmaze_id).first():
        raise HTTPException(400, "Series already in library")
    series = Series(**payload.model_dump())
    db.add(series)
    db.commit()
    db.refresh(series)

    for ep in await tvmaze.get_tv_episodes(payload.tvmaze_id):
        db.add(Episode(series_id=series.id, **ep))
    db.commit()
    return series


@router.delete("/series/{series_id}", status_code=204)
def delete_series(series_id: int, db: Session = Depends(get_db)):
    series = db.get(Series, series_id)
    if series:
        db.query(Episode).filter(Episode.series_id == series_id).delete()
        db.delete(series)
        db.commit()


@router.get("/series/{series_id}/episodes", response_model=list[EpisodeOut])
def list_episodes(series_id: int, db: Session = Depends(get_db)):
    return db.query(Episode).filter(Episode.series_id == series_id).order_by(Episode.season_number, Episode.episode_number).all()


@router.get("/episodes/{episode_id}/candidates", response_model=list[ScoredReleaseOut])
async def episode_candidates(episode_id: int, db: Session = Depends(get_db)):
    episode = db.get(Episode, episode_id)
    if not episode:
        raise HTTPException(404, "Episode not found")
    series = db.get(Series, episode.series_id)

    query = f"{series.title} S{episode.season_number:02d}E{episode.episode_number:02d}"
    profile = db.get(QualityProfile, series.quality_profile_id) if series.quality_profile_id else db.query(QualityProfile).first()
    return await scored_candidates(db, query, profile)


@router.post("/episodes/{episode_id}/grab", response_model=DownloadRecordOut)
async def grab_episode(episode_id: int, payload: GrabRequest, db: Session = Depends(get_db)):
    episode = db.get(Episode, episode_id)
    if not episode:
        raise HTTPException(404, "Episode not found")
    try:
        return await do_grab_episode(db, episode, payload.download_url, payload.release_title)
    except Exception as exc:
        raise HTTPException(502, f"Failed to send to download client: {exc}")
