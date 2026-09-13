"""The background cycle that makes this a PVR instead of a manual tool:
advance in-flight downloads, retire torrents that have finished seeding,
then search+grab anything still missing."""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app import blocklist, health, requests_service, subtitles
from app.candidates import episode_query, movie_query, profile_for, scored_candidates, season_candidates
from app.download_check import check_and_import, reap_seeded
from app.grabber import grab_episode, grab_movie, grab_season
from app.models import DownloadRecord, Episode, Movie, QualityProfile, Series
from app.scoring import beats_current, is_upgradable


UPGRADE_SEARCH_INTERVAL = timedelta(hours=24)
PACK_MISSING_RATIO = 0.6  # search a season pack when at least this share of a season is missing


def _has_active_download(db: Session, *, movie_id: int | None = None, episode_id: int | None = None) -> bool:
    query = db.query(DownloadRecord).filter(DownloadRecord.status.notin_(["imported", "failed"]))
    if movie_id is not None:
        query = query.filter(DownloadRecord.movie_id == movie_id)
    if episode_id is not None:
        query = query.filter(DownloadRecord.episode_id == episode_id)
    return query.first() is not None


def _has_active_pack(db: Session, series_id: int, season_number: int) -> bool:
    return db.query(DownloadRecord).filter(
        DownloadRecord.series_id == series_id, DownloadRecord.season_number == season_number,
        DownloadRecord.status.notin_(["imported", "failed"]),
    ).first() is not None


async def _search_and_grab_movie(db: Session, movie: Movie, profile: QualityProfile) -> bool:
    """Search the movie's profile-filtered candidates and grab the best one. True when grabbed."""
    candidates = await scored_candidates(db, movie_query(movie), profile)
    best = next((c for c in candidates if c["is_best"]), None)
    if not best:
        return False
    try:
        await grab_movie(db, movie, best["download_url"], best["title"], score=best["score"])
        return True
    except Exception:
        return False  # a dead download link shouldn't stop the cycle; next run retries


async def _search_and_grab_episode(db: Session, episode: Episode, series: Series, profile: QualityProfile) -> bool:
    """Search the episode's profile-filtered candidates and grab the best one. True when grabbed."""
    candidates = await scored_candidates(db, episode_query(series, episode), profile)
    best = next((c for c in candidates if c["is_best"]), None)
    if not best:
        return False
    try:
        await grab_episode(db, episode, best["download_url"], best["title"], score=best["score"])
        return True
    except Exception:
        return False  # a dead download link shouldn't stop the cycle; next run retries


async def _search_and_grab_season(db: Session, series: Series, season_number: int, profile: QualityProfile) -> bool:
    """Search for a whole-season pack and grab the best one. True when grabbed."""
    candidates = await season_candidates(db, series, season_number, profile)
    best = next((c for c in candidates if c["is_best"]), None)
    if not best:
        return False
    try:
        await grab_season(db, series, season_number, best["download_url"], best["title"], score=best["score"])
        return True
    except Exception:
        return False


async def _advance_downloads(db: Session) -> None:
    active = db.query(DownloadRecord).filter(DownloadRecord.status.notin_(["imported", "failed"])).all()
    for record in active:
        try:
            await check_and_import(db, record)
        except Exception:
            pass  # one bad download shouldn't stop the rest of the cycle
    try:
        reap_seeded(db)
    except Exception:
        pass


async def _upgrade_titles(db: Session) -> None:
    """Once a day per title: re-search anything that has a file but is still below its
    profile's cutoff or upgrade_until_score, and grab a candidate that clearly beats it."""
    now = datetime.now(timezone.utc)
    due = now - UPGRADE_SEARCH_INTERVAL
    default_profile = db.query(QualityProfile).first()

    for movie in db.query(Movie).filter(Movie.has_file == True).all():  # noqa: E712
        profile = profile_for(db, movie.quality_profile_id, default=default_profile)
        if not profile or not is_upgradable(movie.file_quality, movie.file_score, profile):
            continue
        if movie.last_upgrade_search and movie.last_upgrade_search.replace(tzinfo=timezone.utc) > due:
            continue
        if _has_active_download(db, movie_id=movie.id):
            continue
        movie.last_upgrade_search = now
        db.commit()
        candidates = await scored_candidates(db, movie_query(movie), profile)
        best = next((c for c in candidates if c["is_best"]), None)
        if best and beats_current(best["quality"], best["score"], movie.file_quality, movie.file_score, profile):
            try:
                await grab_movie(db, movie, best["download_url"], best["title"], score=best["score"], upgrade=True)
            except Exception:
                pass

    for episode in db.query(Episode).filter(Episode.has_file == True, Episode.monitored == True).all():  # noqa: E712
        series = db.get(Series, episode.series_id)
        profile = profile_for(db, series.quality_profile_id, default=default_profile) if series else None
        if not profile or not is_upgradable(episode.file_quality, episode.file_score, profile):
            continue
        if episode.last_upgrade_search and episode.last_upgrade_search.replace(tzinfo=timezone.utc) > due:
            continue
        if _has_active_download(db, episode_id=episode.id):
            continue
        episode.last_upgrade_search = now
        db.commit()
        candidates = await scored_candidates(db, episode_query(series, episode), profile)
        best = next((c for c in candidates if c["is_best"]), None)
        if best and beats_current(best["quality"], best["score"], episode.file_quality, episode.file_score, profile):
            try:
                await grab_episode(db, episode, best["download_url"], best["title"], score=best["score"], upgrade=True)
            except Exception:
                pass


async def retry_download(db: Session, record: DownloadRecord) -> bool:
    """Search again for the title behind a (failed) download record and grab the best
    non-blocklisted candidate. True when something was grabbed."""
    default_profile = db.query(QualityProfile).first()
    if record.movie_id:
        movie = db.get(Movie, record.movie_id)
        profile = profile_for(db, movie.quality_profile_id, default=default_profile) if movie else None
        return bool(movie and profile) and await _search_and_grab_movie(db, movie, profile)
    if record.episode_id:
        episode = db.get(Episode, record.episode_id)
        series = db.get(Series, episode.series_id) if episode else None
        profile = profile_for(db, series.quality_profile_id, default=default_profile) if series else None
        return bool(episode and series and profile) and await _search_and_grab_episode(db, episode, series, profile)
    return False


async def _grab_missing_movies(db: Session) -> None:
    default_profile = db.query(QualityProfile).first()
    for movie in db.query(Movie).filter(Movie.has_file == False).all():  # noqa: E712
        if _has_active_download(db, movie_id=movie.id):
            continue
        profile = profile_for(db, movie.quality_profile_id, default=default_profile)
        if not profile:
            continue
        await _search_and_grab_movie(db, movie, profile)


async def _grab_missing_episodes(db: Session) -> None:
    default_profile = db.query(QualityProfile).first()
    missing = db.query(Episode).filter(Episode.has_file == False, Episode.monitored == True).all()  # noqa: E712
    by_season: dict[tuple[int, int], list[Episode]] = {}
    for episode in missing:
        by_season.setdefault((episode.series_id, episode.season_number), []).append(episode)
    for (series_id, season_number), episodes in by_season.items():
        series = db.get(Series, series_id)
        profile = profile_for(db, series.quality_profile_id, default=default_profile) if series else None
        if not series or not profile:
            continue
        if _has_active_pack(db, series_id, season_number):
            continue  # the pack on its way covers these
        total = db.query(Episode).filter(Episode.series_id == series_id, Episode.season_number == season_number).count()
        if total and len(episodes) / total >= PACK_MISSING_RATIO and await _search_and_grab_season(db, series, season_number, profile):
            continue  # got a pack; no per-episode grabs for this season this cycle
        for episode in episodes:
            if _has_active_download(db, episode_id=episode.id):
                continue
            await _search_and_grab_episode(db, episode, series, profile)


async def search_season(db: Session, series: Series, season_number: int) -> bool:
    """Manual 'search season': try a pack first, then each missing monitored episode. True when anything was grabbed."""
    profile = profile_for(db, series.quality_profile_id)
    if not profile:
        return False
    if not _has_active_pack(db, series.id, season_number) and await _search_and_grab_season(db, series, season_number, profile):
        return True
    grabbed = False
    for episode in db.query(Episode).filter(Episode.series_id == series.id, Episode.season_number == season_number, Episode.has_file == False, Episode.monitored == True).all():  # noqa: E712
        if not _has_active_download(db, episode_id=episode.id):
            grabbed = await _search_and_grab_episode(db, episode, series, profile) or grabbed
    return grabbed


async def run_cycle(db: Session) -> None:
    try:
        blocklist.purge_expired(db)
    except Exception:
        pass
    await _advance_downloads(db)
    await _grab_missing_movies(db)
    await _grab_missing_episodes(db)
    try:
        await _upgrade_titles(db)
    except Exception:
        pass  # upgrades are best-effort; the next cycle retries
    try:
        await requests_service.mark_available(db)
    except Exception:
        pass  # a notification problem must never break the cycle
    try:
        await health.run(db)
    except Exception:
        pass  # health checks are advisory
    try:
        await subtitles.fetch_missing(db)
    except Exception:
        pass  # subtitle fetch is best-effort; the next cycle retries
