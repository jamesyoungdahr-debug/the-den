"""Advance one DownloadRecord against the built-in torrent engine, importing it when
done -- and, separately, clean up torrents that have finished their seeding duty."""

from sqlalchemy.orm import Session

from app import importer, settings as settings_module
from app.models import DownloadRecord, Episode, Movie, Series
from app.notifier import notify
from app.torrent import engine

TERMINAL_STATUSES = ("imported", "failed")


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
    if st is None:
        record.status = "failed"  # removed from the engine, or its state was lost
    elif st.error:
        record.status = "failed"
    elif st.is_finished:
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
        imported = importer.import_movie(files, movie, s.movies_root)
        if imported:
            movie.has_file = True
    elif record.episode_id:
        episode = db.get(Episode, record.episode_id)
        series = db.get(Series, episode.series_id) if episode else None
        if episode is None or series is None:
            record.status = "failed"
            return
        imported = importer.import_episode(files, series, episode, s.tv_root)
        if imported:
            episode.has_file = True
    # "completed" = finished downloading but nothing importable in it (no video file).
    record.status = "imported" if imported else "completed"
    if imported:
        await notify(f"Imported: {record.release_title}", s.discord_webhook_url)


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
