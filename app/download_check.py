from sqlalchemy.orm import Session

from app import importer, qbittorrent
from app.models import DownloadRecord, Episode, Movie, Series
from app.notifier import notify


async def check_and_import(db: Session, record: DownloadRecord) -> None:
    """Poll qBittorrent for this download and import it if finished. Mutates + commits record."""
    if record.status == "imported":
        return

    info = await qbittorrent.get_by_category(record.category)

    if info is None:
        record.status = "queued"
    elif info.get("progress", 0) >= 1.0:
        imported = False
        if record.movie_id:
            movie = db.get(Movie, record.movie_id)
            imported = importer.import_movie(info, movie)
            if imported:
                movie.has_file = True
        elif record.episode_id:
            episode = db.get(Episode, record.episode_id)
            series = db.get(Series, episode.series_id)
            imported = importer.import_episode(info, series, episode)
            if imported:
                episode.has_file = True
        record.status = "imported" if imported else "completed"
        if imported:
            await notify(f"Imported: {record.release_title}")
    else:
        record.status = "downloading"

    db.commit()
