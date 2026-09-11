"""Send a chosen release to the built-in torrent engine and record it."""

from sqlalchemy.orm import Session

from app import settings as settings_module
from app.models import DownloadRecord, Episode, Movie
from app.notifier import notify
from app.torrent import engine


async def _grab(
    db: Session, *, download_url: str, release_title: str, label: str,
    movie_id: int | None = None, episode_id: int | None = None,
) -> DownloadRecord:
    s = settings_module.effective(db)
    info_hash = await engine.add(download_url, save_path=s.downloads_root)
    record = DownloadRecord(
        movie_id=movie_id, episode_id=episode_id, release_title=release_title,
        download_url=download_url, info_hash=info_hash, status="queued",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    await notify(f"Grabbed **{label}** -- {release_title}", s.discord_webhook_url)
    return record


async def grab_movie(db: Session, movie: Movie, download_url: str, release_title: str) -> DownloadRecord:
    return await _grab(
        db, download_url=download_url, release_title=release_title,
        label=f"{movie.title} ({movie.year})", movie_id=movie.id,
    )


async def grab_episode(db: Session, episode: Episode, download_url: str, release_title: str) -> DownloadRecord:
    return await _grab(
        db, download_url=download_url, release_title=release_title,
        label=f"S{episode.season_number:02d}E{episode.episode_number:02d}", episode_id=episode.id,
    )
