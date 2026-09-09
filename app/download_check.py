from sqlalchemy.orm import Session

from app import importer, qbittorrent, settings as settings_module
from app.models import DownloadRecord, Episode, Movie, Series
from app.notifier import notify


async def check_and_import(db: Session, record: DownloadRecord) -> None:
    """Poll qBittorrent for this download and import it if finished. Mutates + commits record."""
    if record.status == "imported":
        return

    s = settings_module.effective(db)
    info = await qbittorrent.get_by_category(
        record.category, url=s.qbit_url, username=s.qbit_username, password=s.qbit_password
    )

    if info is None:
        record.status = "queued"
    elif info.get("progress", 0) >= 1.0:
        imported = False
        if record.movie_id:
            movie = db.get(Movie, record.movie_id)
            if movie is None:
                record.status = "failed"
                db.commit()
                return
            imported = importer.import_movie(info, movie, s.movies_root)
            if imported:
                movie.has_file = True
        elif record.episode_id:
            episode = db.get(Episode, record.episode_id)
            series = db.get(Series, episode.series_id) if episode else None
            if episode is None or series is None:
                record.status = "failed"
                db.commit()
                return
            imported = importer.import_episode(info, series, episode, s.tv_root)
            if imported:
                episode.has_file = True
        record.status = "imported" if imported else "completed"
        if imported:
            await notify(f"Imported: {record.release_title}", s.discord_webhook_url)
    else:
        record.status = "downloading"

    db.commit()
