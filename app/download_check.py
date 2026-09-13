"""Advance one DownloadRecord against the built-in torrent engine, importing it when
done -- and, separately, clean up torrents that have finished their seeding duty."""

import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app import blocklist, history, importer, root_folders, settings as settings_module
from app.models import DownloadRecord, Episode, Movie, Series
from app.notifier import notify_event
from app.torrent import engine

TERMINAL_STATUSES = ("imported", "failed")

STALL_MINUTES = 30  # no progress and no seeders for this long -> stalled
METADATA_MINUTES = 20  # magnet never resolved -> dead


def _utc(dt: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; treat them as UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


async def fail_download(db: Session, record: DownloadRecord, reason: str, blocklist_days: int | None = 30) -> None:
    """Give up on a download: blocklist the release, remove the torrent and its data, mark
    the record failed and notify. The next automation cycle searches again."""
    s = settings_module.effective(db)
    if record.status != "failed":
        blocklist.add(db, record, reason, days=blocklist_days)
    if record.info_hash:
        try:
            engine.remove(record.info_hash, delete_files=True)
        except Exception:
            pass
    record.status = "failed"
    record.failure_reason = reason
    db.commit()
    history.record(db, "download_failed", record.release_title, movie_id=record.movie_id, episode_id=record.episode_id, series_id=record.series_id, season_number=record.season_number, message=reason)
    await notify_event(db, "download_failed", f"Download failed ({reason}): {record.release_title}", legacy_discord_url=s.discord_webhook_url, link="theden://downloads")


async def check_and_import(db: Session, record: DownloadRecord) -> None:
    """Refresh record.status from the engine and import the file once it's finished.
    Mutates + commits record."""
    if record.status in TERMINAL_STATUSES:
        return
    if not record.info_hash:
        # Predates the built-in engine (was tracked in an external qBittorrent); nothing to poll.
        record.status = "failed"
        db.commit()
        return

    st = engine.status(record.info_hash)
    now = datetime.now(timezone.utc)
    if st is None:
        record.status = "failed"  # removed from the engine, or its state was lost
        record.failure_reason = record.failure_reason or "gone from the engine"
        db.commit()
        return
    if st.progress > (record.last_progress or 0.0) or record.last_progress_at is None:
        record.last_progress = st.progress
        record.last_progress_at = now
    since_progress = now - (_utc(record.last_progress_at) or _utc(record.created_at) or now)
    if st.error:
        await fail_download(db, record, f"error: {st.error}")
        return
    if st.state == "metadata" and since_progress > timedelta(minutes=METADATA_MINUTES):
        await fail_download(db, record, f"dead: no metadata after {METADATA_MINUTES} min")
        return
    if st.state in ("downloading", "queued") and not st.is_finished and st.num_seeds == 0 and st.download_rate == 0 and since_progress > timedelta(minutes=STALL_MINUTES):
        await fail_download(db, record, f"stalled: no progress for {STALL_MINUTES} min with no seeders")
        return
    if st.is_finished:
        await _import(db, record)
    elif st.state in ("metadata", "checking", "queued"):
        record.status = "queued"
    else:
        record.status = "downloading"
    db.commit()


async def _import(db: Session, record: DownloadRecord) -> None:
    s = settings_module.effective(db)
    files = engine.files(record.info_hash)
    done = {}
    imported = False
    if not record.movie_id and not record.episode_id and not (record.series_id and record.season_number is not None):
        names = [f.path.split("/")[-1].split("\\")[-1] for f in files if not f.path.lower().endswith((".txt", ".nfo", ".jpg", ".png", ".srt", ".sub"))]
        record.unmatched_files = json.dumps(names) if names else None
        record.status = "completed"
        return
    if record.movie_id:
        movie = db.get(Movie, record.movie_id)
        if movie is None:
            record.status = "failed"
            return
        movies_root = root_folders.root_folder_for(db, movie.root_folder_id, "movie", s.movies_root)
        dest = importer.import_movie(files, movie, movies_root, replace=movie.file_path if record.upgrade else None)
        if dest:
            movie.has_file = True
            movie.file_quality = record.quality
            movie.file_score = record.score or 0
            movie.file_path = str(dest)
            imported = True
        else:
            names = [f.path.split("/")[-1].split("\\")[-1] for f in files if not f.path.lower().endswith((".txt", ".nfo", ".jpg", ".png", ".srt", ".sub"))]
            record.unmatched_files = json.dumps(names) if names else None
            record.failure_reason = record.failure_reason or "no video file found in this torrent"
    elif record.series_id and record.season_number is not None:
        series = db.get(Series, record.series_id)
        if series is None:
            record.status = "failed"
            return
        season_eps = db.query(Episode).filter(Episode.series_id == series.id, Episode.season_number == record.season_number).all()
        tv_root = root_folders.root_folder_for(db, series.root_folder_id, "tv", s.tv_root)
        done, unmatched = importer.import_season_pack(files, series, record.season_number, {e.episode_number: e for e in season_eps}, tv_root)
        for e in season_eps:
            if e.episode_number in done:
                e.has_file = True
                e.file_quality = record.quality
                e.file_score = record.score or 0
                e.file_path = str(done[e.episode_number])
        imported = bool(done)
        if unmatched:
            record.unmatched_files = json.dumps(unmatched)
            record.failure_reason = f"{len(unmatched)} file(s) matched no episode: " + ", ".join(unmatched[:5])
    elif record.episode_id:
        episode = db.get(Episode, record.episode_id)
        series = db.get(Series, episode.series_id) if episode else None
        if episode is None or series is None:
            record.status = "failed"
            return
        tv_root = root_folders.root_folder_for(db, series.root_folder_id, "tv", s.tv_root)
        dest = importer.import_episode(files, series, episode, tv_root, replace=episode.file_path if record.upgrade else None)
        if dest:
            episode.has_file = True
            episode.file_quality = record.quality
            episode.file_score = record.score or 0
            episode.file_path = str(dest)
            imported = True
        else:
            names = [f.path.split("/")[-1].split("\\")[-1] for f in files if not f.path.lower().endswith((".txt", ".nfo", ".jpg", ".png", ".srt", ".sub"))]
            record.unmatched_files = json.dumps(names) if names else None
            record.failure_reason = record.failure_reason or "no video file found in this torrent"
    # "completed" = finished downloading but nothing importable in it (no video file).
    record.status = "imported" if imported else "completed"
    if imported:
        event = "upgraded" if record.upgrade else "imported"
        prefix = "Upgraded" if record.upgrade else "Imported"
        what = record.release_title
        if record.series_id and record.season_number is not None:
            what = f"{record.release_title} ({len(done)} episodes)"
        history.record(db, event, record.release_title, movie_id=record.movie_id, episode_id=record.episode_id, series_id=record.series_id, season_number=record.season_number, message=what)
        await notify_event(db, event, f"{prefix}: {what}", legacy_discord_url=s.discord_webhook_url, link="theden://downloads")


def reap_seeded(db: Session) -> int:
    """Remove torrents (data included) once they're both imported into the library and
    past their seeding limits -- the engine parks those as "done". Torrents the user
    added by hand (no record) and anything still seeding are left alone."""
    reaped = 0
    records = db.query(DownloadRecord).filter(
        DownloadRecord.status == "imported", DownloadRecord.info_hash.isnot(None), DownloadRecord.unmatched_files.is_(None)
    ).all()
    for record in records:
        st = engine.status(record.info_hash)
        if st is not None and st.state == "done":
            engine.remove(record.info_hash, delete_files=True)
            if record.movie_id or record.episode_id or record.series_id:
                history.record(db, "removed", record.release_title, movie_id=record.movie_id, episode_id=record.episode_id, series_id=record.series_id, season_number=record.season_number, message="seeding finished, removed from client")
            reaped += 1
    return reaped
