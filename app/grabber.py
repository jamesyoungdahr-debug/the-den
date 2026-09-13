"""Send a chosen release to the built-in torrent engine and record it."""

from sqlalchemy.orm import Session

from app import settings as settings_module
from app import formats
from app import history
from app.models import DownloadRecord, Episode, Movie, Series
from app.candidates import profile_for
from app.notifier import notify_event
from app.parser import parse_quality
from app.torrent import engine


def _score_for(db: Session, quality_profile_id: int | None, release_title: str) -> int:
    """The release's custom-format score under the title's quality profile (0 without one)."""
    profile = profile_for(db, quality_profile_id)
    if profile is None:
        return 0
    return formats.score_title(release_title, formats.profile_scores(db, profile))[0]


async def _grab(
    db: Session, *, download_url: str, release_title: str, label: str,
    movie_id: int | None = None, episode_id: int | None = None, series_id: int | None = None, season_number: int | None = None,
    score: int = 0, upgrade: bool = False,
) -> DownloadRecord:
    s = settings_module.effective(db)
    info_hash = await engine.add(download_url, save_path=s.downloads_root)
    record = DownloadRecord(
        movie_id=movie_id, episode_id=episode_id, series_id=series_id, season_number=season_number, release_title=release_title,
        download_url=download_url, info_hash=info_hash, status="queued",
        quality=parse_quality(release_title), score=score, upgrade=upgrade,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    history.record(db, "upgraded" if upgrade else "grabbed", release_title, movie_id=movie_id, episode_id=episode_id, series_id=series_id, season_number=season_number, message=label)
    await notify_event(db, "grabbed", f"{'Upgrade grabbed' if upgrade else 'Grabbed'} **{label}** -- {release_title}", legacy_discord_url=s.discord_webhook_url, link="theden://downloads")
    return record


async def grab_movie(db: Session, movie: Movie, download_url: str, release_title: str, score: int | None = None, upgrade: bool | None = None) -> DownloadRecord:
    if score is None:
        score = _score_for(db, movie.quality_profile_id, release_title)
    if upgrade is None:
        upgrade = bool(movie.has_file)
    return await _grab(
        db, download_url=download_url, release_title=release_title,
        label=f"{movie.title} ({movie.year})", movie_id=movie.id,
        score=score, upgrade=upgrade,
    )


async def grab_episode(db: Session, episode: Episode, download_url: str, release_title: str, score: int | None = None, upgrade: bool | None = None) -> DownloadRecord:
    series = db.get(Series, episode.series_id)
    if score is None:
        score = _score_for(db, series.quality_profile_id if series else None, release_title)
    if upgrade is None:
        upgrade = bool(episode.has_file)
    return await _grab(
        db, download_url=download_url, release_title=release_title,
        label=f"S{episode.season_number:02d}E{episode.episode_number:02d}", episode_id=episode.id,
        score=score, upgrade=upgrade,
    )


async def grab_season(db: Session, series: Series, season_number: int, download_url: str, release_title: str, score: int | None = None) -> DownloadRecord:
    """Grab a whole-season pack; every episode file in it is imported when it finishes."""
    if score is None:
        score = _score_for(db, series.quality_profile_id, release_title)
    return await _grab(
        db, download_url=download_url, release_title=release_title,
        label=f"{series.title} S{season_number:02d}", series_id=series.id, season_number=season_number, score=score,
    )
