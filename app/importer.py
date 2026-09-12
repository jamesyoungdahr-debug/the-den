"""Place a finished download into the library. Hard-links when the library and the
downloads folder share a filesystem (instant, no extra space) and falls back to a
copy -- either way the torrent keeps seeding from where it is. Files are renamed to
Plex's conventions (`Title (Year).ext`, `Show - S01E02 - Episode.ext`) inside the
existing folder layout."""

import os
import re
import shutil
from pathlib import Path

from app.models import Episode, Movie, Series
from app.torrent import TorrentFile

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".m4v", ".mov", ".ts", ".wmv"}


def _safe_name(name: str) -> str:
    """Strip characters that can't be in a folder name (or would nest one: '/')."""
    return re.sub(r'[<>:"/\\|?*]', "", name).strip() or "untitled"


def movie_name(movie: Movie) -> str:
    """Plex's movie convention: `Title (Year)`, or just the title when the year is unknown."""
    return _safe_name(f"{movie.title} ({movie.year})") if movie.year else _safe_name(movie.title)


def episode_name(series: Series, episode: Episode) -> str:
    """Plex's episode convention: `Show - S01E02 - Episode title` (title part optional)."""
    return _safe_name(f"{series.title} - S{episode.season_number:02d}E{episode.episode_number:02d}" + (f" - {episode.title}" if episode.title else ""))


def _largest_video_file(files: list[TorrentFile]) -> Path | None:
    candidates = [Path(f.path) for f in files if Path(f.path).suffix.lower() in VIDEO_EXTENSIONS]
    candidates = [p for p in candidates if p.is_file()]
    return max(candidates, key=lambda p: p.stat().st_size, default=None)


def _link_into(files: list[TorrentFile], dest_dir: Path, name: str | None = None) -> bool:
    source = _largest_video_file(files)
    if source is None:
        return False
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (name + source.suffix.lower()) if name else dest_dir / source.name
    if dest.exists():
        return True  # already imported -- e.g. re-checked after a restart
    try:
        os.link(source, dest)
    except OSError:
        shutil.copy2(source, dest)  # different filesystem, or one without hard links
    return True


def import_movie(files: list[TorrentFile], movie: Movie, movies_root: str) -> bool:
    name = movie_name(movie)
    dest_dir = Path(movies_root) / name
    return _link_into(files, dest_dir, name=name)


def import_episode(files: list[TorrentFile], series: Series, episode: Episode, tv_root: str) -> bool:
    dest_dir = Path(tv_root) / _safe_name(series.title) / f"Season {episode.season_number:02d}"
    name = episode_name(series, episode)
    return _link_into(files, dest_dir, name=name)
