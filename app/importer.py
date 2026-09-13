"""Place a finished download into the library. Hard-links when the library and the
downloads folder share a filesystem (instant, no extra space) and falls back to a
copy -- either way the torrent keeps seeding from where it is. Files are renamed to
Plex's conventions (`Title (Year).ext`, `Show - S01E02 - Episode.ext`) inside the
existing folder layout. An upgrade links the new file next to the old one, swaps it in atomically and removes the old file afterwards."""

import os
import re
import shutil
from pathlib import Path

from app.models import Episode, Movie, Series
from app.parser import parse_episode
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


def _link_into(files: list[TorrentFile], dest_dir: Path, name: str | None = None, replace: Path | None = None) -> Path | None:
    source = _largest_video_file(files)
    if source is None:
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (name + source.suffix.lower()) if name else dest_dir / source.name
    if replace is None and dest.exists():
        return dest  # already imported -- e.g. re-checked after a restart
    tmp = dest.with_name(dest.name + ".upgrading")
    try:
        os.unlink(tmp)
    except OSError:
        pass
    try:
        os.link(source, tmp)
    except OSError:
        shutil.copy2(source, tmp)  # different filesystem, or one without hard links
    if tmp.stat().st_size <= 0:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return None
    os.replace(tmp, dest)
    if replace is not None and replace != dest and replace.exists():
        try:
            replace.unlink()
        except OSError:
            pass
        # Clean up empty parent directory if needed
        if replace.parent != dest.parent and not any(replace.parent.iterdir()):
            try:
                replace.parent.rmdir()
            except OSError:
                pass
    return dest


def import_movie(files: list[TorrentFile], movie: Movie, movies_root: str, replace: str | None = None) -> Path | None:
    name = movie_name(movie)
    dest_dir = Path(movies_root) / name
    return _link_into(files, dest_dir, name=name, replace=Path(replace) if replace else None)


def import_episode(files: list[TorrentFile], series: Series, episode: Episode, tv_root: str, replace: str | None = None) -> Path | None:
    dest_dir = Path(tv_root) / _safe_name(series.title) / f"Season {episode.season_number:02d}"
    name = episode_name(series, episode)
    return _link_into(files, dest_dir, name=name, replace=Path(replace) if replace else None)


def import_season_pack(files: list[TorrentFile], series: Series, season_number: int, episodes: dict[int, Episode], tv_root: str) -> tuple[dict[int, Path], list[str]]:
    """Import every video file of a multi-episode torrent to the episode it names.
    `episodes` maps episode number -> Episode for this season. Returns
    ({episode_number: library path written}, [file names that matched no episode]).
    Files whose parsed season differs from `season_number`, or whose episode is not in
    `episodes`, count as unmatched. Samples (name contains 'sample') are skipped silently."""
    dest_dir = Path(tv_root) / _safe_name(series.title) / f"Season {season_number:02d}"
    imported: dict[int, Path] = {}
    unmatched: list[str] = []
    for f in files:
        source = Path(f.path)
        if source.suffix.lower() not in VIDEO_EXTENSIONS or not source.is_file():
            continue
        if "sample" in source.name.lower():
            continue
        parsed = parse_episode(source.name)
        if parsed is None or parsed[0] != season_number or parsed[1] not in episodes:
            unmatched.append(source.name)
            continue
        episode = episodes[parsed[1]]
        dest = _link_into([f], dest_dir, name=episode_name(series, episode), replace=Path(episode.file_path) if episode.file_path else None)
        if dest is not None:
            imported[parsed[1]] = dest
    return imported, unmatched
