"""The background cycle that makes this a PVR instead of a manual tool:
advance in-flight downloads, then search+grab anything still missing."""

from sqlalchemy.orm import Session

from app.candidates import scored_candidates
from app.download_check import check_and_import
from app.grabber import grab_episode, grab_movie
from app.models import DownloadRecord, Episode, Movie, QualityProfile, Series


def _has_active_download(db: Session, *, movie_id: int | None = None, episode_id: int | None = None) -> bool:
    query = db.query(DownloadRecord).filter(DownloadRecord.status.notin_(["imported", "failed"]))
    if movie_id is not None:
        query = query.filter(DownloadRecord.movie_id == movie_id)
    if episode_id is not None:
        query = query.filter(DownloadRecord.episode_id == episode_id)
    return query.first() is not None


async def _advance_downloads(db: Session) -> None:
    active = db.query(DownloadRecord).filter(DownloadRecord.status != "imported").all()
    for record in active:
        try:
            await check_and_import(db, record)
        except Exception:
            pass  # download client hiccup shouldn't stop the rest of the cycle


async def _grab_missing_movies(db: Session) -> None:
    default_profile = db.query(QualityProfile).first()
    for movie in db.query(Movie).filter(Movie.has_file == False).all():  # noqa: E712
        if _has_active_download(db, movie_id=movie.id):
            continue
        profile = db.get(QualityProfile, movie.quality_profile_id) if movie.quality_profile_id else default_profile
        if not profile:
            continue
        query = f"{movie.title} {movie.year}" if movie.year else movie.title
        candidates = await scored_candidates(db, query, profile)
        best = next((c for c in candidates if c["is_best"]), None)
        if best:
            await grab_movie(db, movie, best["download_url"], best["title"])


async def _grab_missing_episodes(db: Session) -> None:
    default_profile = db.query(QualityProfile).first()
    for episode in db.query(Episode).filter(Episode.has_file == False).all():  # noqa: E712
        if _has_active_download(db, episode_id=episode.id):
            continue
        series = db.get(Series, episode.series_id)
        profile = db.get(QualityProfile, series.quality_profile_id) if series.quality_profile_id else default_profile
        if not profile:
            continue
        query = f"{series.title} S{episode.season_number:02d}E{episode.episode_number:02d}"
        candidates = await scored_candidates(db, query, profile)
        best = next((c for c in candidates if c["is_best"]), None)
        if best:
            await grab_episode(db, episode, best["download_url"], best["title"])


async def run_cycle(db: Session) -> None:
    await _advance_downloads(db)
    await _grab_missing_movies(db)
    await _grab_missing_episodes(db)
