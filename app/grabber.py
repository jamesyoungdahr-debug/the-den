from sqlalchemy.orm import Session

from app import qbittorrent, settings as settings_module
from app.models import DownloadRecord, Episode, Movie
from app.notifier import notify


async def grab_movie(db: Session, movie: Movie, download_url: str, release_title: str) -> DownloadRecord:
    s = settings_module.effective(db)
    category = f"the-den-movie-{movie.id}"
    await qbittorrent.add_torrent(
        download_url, category, url=s.qbit_url, username=s.qbit_username, password=s.qbit_password
    )
    record = DownloadRecord(
        movie_id=movie.id, release_title=release_title, download_url=download_url,
        category=category, status="queued",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    await notify(f"Grabbed **{movie.title} ({movie.year})** — {release_title}", s.discord_webhook_url)
    return record


async def grab_episode(db: Session, episode: Episode, download_url: str, release_title: str) -> DownloadRecord:
    s = settings_module.effective(db)
    category = f"the-den-episode-{episode.id}"
    await qbittorrent.add_torrent(
        download_url, category, url=s.qbit_url, username=s.qbit_username, password=s.qbit_password
    )
    record = DownloadRecord(
        episode_id=episode.id, release_title=release_title, download_url=download_url,
        category=category, status="queued",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    await notify(f"Grabbed **S{episode.season_number:02d}E{episode.episode_number:02d}** — {release_title}", s.discord_webhook_url)
    return record
