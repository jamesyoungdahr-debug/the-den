from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth, tvmaze
from app.candidates import episode_query, profile_for, scored_candidates
from app.deps import get_db
from app.grabber import grab_episode as do_grab_episode
from app.models import DownloadRecord, Episode, Series
from app.schemas import DownloadRecordOut, EpisodeOut, GrabRequest, ScoredReleaseOut, SeriesCreate, SeriesOut
from app.scoring import is_upgradable

router = APIRouter(tags=["series"])


@router.get("/series/search-tvmaze", dependencies=[Depends(auth.require_user)])
async def search_tvmaze(q: str):
    return await tvmaze.search_tv(q)


@router.get("/series", response_model=list[SeriesOut], dependencies=[Depends(auth.require_user)])
def list_series(db: Session = Depends(get_db)):
    return db.query(Series).all()


@router.post("/series", response_model=SeriesOut, status_code=201, dependencies=[Depends(auth.require_admin)])
async def add_series(payload: SeriesCreate, db: Session = Depends(get_db)):
    if db.query(Series).filter(Series.tvmaze_id == payload.tvmaze_id).first():
        raise HTTPException(400, "Series already in library")

    # Fetch episodes before committing anything: if this raises, nothing's been
    # added yet, so the uniqueness check above won't block a retry with the same
    # tvmaze_id -- unlike committing the series first and fetching episodes after.
    episodes = await tvmaze.get_tv_episodes(payload.tvmaze_id)

    series = Series(**payload.model_dump())
    db.add(series)
    try:
        db.commit()
    except IntegrityError:
        # Two concurrent adds for the same tvmaze_id both passed the check above --
        # the loser hits the DB's unique constraint instead. Same clean error either way.
        db.rollback()
        raise HTTPException(400, "Series already in library")
    db.refresh(series)

    for ep in episodes:
        db.add(Episode(series_id=series.id, **ep))
    db.commit()
    return series


@router.delete("/series/{series_id}", status_code=204, dependencies=[Depends(auth.require_admin)])
def delete_series(series_id: int, db: Session = Depends(get_db)):
    series = db.get(Series, series_id)
    if series:
        episode_ids = [e.id for e in db.query(Episode.id).filter(Episode.series_id == series_id)]
        # Mark any in-flight download as failed rather than leaving it pointing at an
        # episode that's about to stop existing -- check_and_import() dereferences
        # record.episode_id unconditionally and has no way to know it's gone.
        if episode_ids:
            db.query(DownloadRecord).filter(
                DownloadRecord.episode_id.in_(episode_ids),
                DownloadRecord.status.notin_(["imported", "failed"]),
            ).update({"status": "failed"})
        db.query(Episode).filter(Episode.series_id == series_id).delete()
        db.delete(series)
        db.commit()


@router.get("/series/{series_id}/episodes", response_model=list[EpisodeOut], dependencies=[Depends(auth.require_user)])
def list_episodes(series_id: int, db: Session = Depends(get_db)):
    series = db.get(Series, series_id)
    profile = profile_for(db, series.quality_profile_id if series else None)
    out = []
    for episode in db.query(Episode).filter(Episode.series_id == series_id).order_by(Episode.season_number, Episode.episode_number).all():
        item = EpisodeOut.model_validate(episode)
        item.upgradable = bool(episode.has_file and profile and is_upgradable(episode.file_quality, episode.file_score, profile))
        out.append(item)
    return out


@router.get("/episodes/{episode_id}/candidates", response_model=list[ScoredReleaseOut], dependencies=[Depends(auth.require_admin)])
async def episode_candidates(episode_id: int, db: Session = Depends(get_db)):
    episode = db.get(Episode, episode_id)
    if not episode:
        raise HTTPException(404, "Episode not found")
    series = db.get(Series, episode.series_id)
    if not series:
        raise HTTPException(404, "Series not found")

    query = episode_query(series, episode)
    profile = profile_for(db, series.quality_profile_id)
    return await scored_candidates(db, query, profile)


@router.post("/episodes/{episode_id}/grab", response_model=DownloadRecordOut, dependencies=[Depends(auth.require_admin)])
async def grab_episode(episode_id: int, payload: GrabRequest, db: Session = Depends(get_db)):
    episode = db.get(Episode, episode_id)
    if not episode:
        raise HTTPException(404, "Episode not found")
    try:
        return await do_grab_episode(db, episode, payload.download_url, payload.release_title)
    except Exception as exc:
        raise HTTPException(502, f"Failed to send to download client: {exc}")
