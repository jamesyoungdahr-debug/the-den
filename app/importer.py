import shutil
from pathlib import Path

from app import config
from app.models import Movie

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi"}


def _largest_video_file(content_path: str) -> Path | None:
    path = Path(content_path)
    if path.is_file():
        return path if path.suffix.lower() in VIDEO_EXTENSIONS else None
    if path.is_dir():
        candidates = [p for p in path.rglob("*") if p.suffix.lower() in VIDEO_EXTENSIONS]
        return max(candidates, key=lambda p: p.stat().st_size, default=None)
    return None


def import_finished_download(torrent_info: dict, movie: Movie) -> bool:
    """Move the downloaded video file into the library. Returns True if imported."""
    content_path = torrent_info.get("content_path") or torrent_info.get("save_path")
    if not content_path:
        return False

    source = _largest_video_file(content_path)
    if source is None:
        return False

    dest_dir = Path(config.MOVIES_ROOT) / f"{movie.title} ({movie.year})"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / source.name
    shutil.move(str(source), str(dest))
    return True
