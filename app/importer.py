import shutil
from pathlib import Path

from app.models import Episode, Movie, Series

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi"}


def _largest_video_file(content_path: str) -> Path | None:
    path = Path(content_path)
    if path.is_file():
        return path if path.suffix.lower() in VIDEO_EXTENSIONS else None
    if path.is_dir():
        candidates = [p for p in path.rglob("*") if p.suffix.lower() in VIDEO_EXTENSIONS]
        return max(candidates, key=lambda p: p.stat().st_size, default=None)
    return None


def _move_into(torrent_info: dict, dest_dir: Path) -> bool:
    content_path = torrent_info.get("content_path") or torrent_info.get("save_path")
    if not content_path:
        return False
    source = _largest_video_file(content_path)
    if source is None:
        return False
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest_dir / source.name))
    return True


def import_movie(torrent_info: dict, movie: Movie, movies_root: str) -> bool:
    dest_dir = Path(movies_root) / f"{movie.title} ({movie.year})"
    return _move_into(torrent_info, dest_dir)


def import_episode(torrent_info: dict, series: Series, episode: Episode, tv_root: str) -> bool:
    dest_dir = Path(tv_root) / series.title / f"Season {episode.season_number:02d}"
    return _move_into(torrent_info, dest_dir)
