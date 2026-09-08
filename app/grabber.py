from sqlalchemy.orm import Session

from app import qbittorrent
from app.models import DownloadRecord, Episode, Movie


async def grab_movie(db: Session, movie: Movie, download_url: str, release_title: str) -> DownloadRecord:
    category = f"the-den-movie-{movie.id}"
    await qbittorrent.add_torrent(download_url, category)
    record = DownloadRecord(
        movie_id=movie.id, release_title=release_title, download_url=download_url,
        category=category, status="queued",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


async def grab_episode(db: Session, episode: Episode, download_url: str, release_title: str) -> DownloadRecord:
    category = f"the-den-episode-{episode.id}"
    await qbittorrent.add_torrent(download_url, category)
    record = DownloadRecord(
        episode_id=episode.id, release_title=release_title, download_url=download_url,
        category=category, status="queued",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
