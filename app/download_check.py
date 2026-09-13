"""Advance one DownloadRecord against the built-in torrent engine, importing it when
done -- and, separately, clean up torrents that have finished their seeding duty."""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app import blocklist, importer, settings as settings_module
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
    await notify_event(db, "download_failed", f"Download failed ({reason}): {record.release_title}", legacy_discord_url=s.discord_webhook_url)


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
    imported = False
    if record.movie_id:
        movie = db.get(Movie, record.movie_id)
        if movie is None:
            record.status = "failed"
            return
        dest = importer.import_movie(files, movie, s.movies_root, replace=movie.file_path if record.upgrade else None)
        if dest:
            movie.has_file = True
            movie.file_quality = record.quality
            movie.file_score = record.score or 0
            movie.file_path = str(dest)
            imported = True
    elif record.episode_id:
        episode = db.get(Episode, record.episode_id)
        series = db.get(Series, episode.series_id) if episode else None
        if episode is None or series is None:
            record.status = "failed"
            return
        dest = importer.import_episode(files, series, episode, s.tv_root, replace=episode.file_path if record.upgrade else None)
        if dest:
            episode.has_file = True
            episode.file_quality = record.quality
            episode.file_score = record.score or 0
            episode.file_path = str(dest)
            imported = True
    # "completed" = finished downloading but nothing importable in it (no video file).
    record.status = "imported" if imported else "completed"
    if imported:
        event = "upgraded" if record.upgrade else "imported"
        prefix = "Upgraded" if record.upgrade else "Imported"
        await notify_event(db, event, f"{prefix}: {record.release_title}", legacy_discord_url=s.discord_webhook_url)


def reap_seeded(db: Session) -> int:
    """Remove torrents (data included) once they're both imported into the library and
    past their seeding limits -- the engine parks those as "done". Torrents the user
    added by hand (no record) and anything still seeding are left alone."""
    reaped = 0
    records = db.query(DownloadRecord).filter(
        DownloadRecord.status == "imported", DownloadRecord.info_hash.isnot(None)
    ).all()
    for record in records:
        st = engine.status(record.info_hash)
        if st is not None and st.state == "done":
            engine.remove(record.info_hash, delete_files=True)
            reaped += 1
    return reaped
