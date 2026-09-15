"""M50a - The Den's own library scan.
Walks the configured library folders, records every video file in media_files, matches files to their Movie or Episode row, and notices files that appear, change or vanish between runs.
The scan only stats paths and reads the database; it never opens a file's contents, so it is safe to run on a schedule. Matching is deliberately conservative: a file is matched only when its name is unambiguous, otherwise it is recorded with matched=False and both owner columns NULL for a person to place later.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app import settings as settings_module
from app.models import Episode, MediaFile, Movie, RootFolder, Series
from app.parser import parse_episode, parse_movie, parse_quality

log = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".m4v", ".mov", ".ts", ".m2ts", ".webm", ".wmv"}

# Torrent releases ship samples, ad folders and artwork beside the feature; never descend into them.
SKIP_DIR_NAMES = {"@eadir", "extrafanout", "sample", "samples", ".actors"}

SEASON_DIR_RE = re.compile(r"^(?:season|s)[\s._-]*(\d{1,2})$", re.IGNORECASE)


def _norm(title: str | None) -> str:
    """Lowercase a title and collapse every run of non-alphanumerics to a single space."""
    if not title:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _real(path: str) -> str:
    """Canonicalise a path so the same folder is never scanned twice."""
    return os.path.normcase(os.path.realpath(os.path.expanduser(path)))


def library_folders(db: Session) -> list[tuple[str, str, int | None]]:
    """Return (real_path, media_type, root_folder_id) for every configured folder that exists."""
    candidates: list[tuple[str | None, str, int | None]] = [
        (row.path, row.media_type, row.id) for row in db.query(RootFolder).all()
    ]
    config = settings_module.effective(db)
    candidates.append((config.movies_root, "movie", None))
    candidates.append((config.tv_root, "tv", None))

    folders: list[tuple[str, str, int | None]] = []
    seen: set[str] = set()
    for path, media_type, root_folder_id in candidates:
        if not path:
            continue
        real = _real(path)
        if real in seen:
            # A folder configured twice would record every file in it twice.
            continue
        if not os.path.isdir(real):
            continue
        seen.add(real)
        folders.append((real, media_type, root_folder_id))
    log.debug("library_folders: %d usable folder(s)", len(folders))
    return folders


def walk_videos(folder: str) -> list[str]:
    """Return every video file under folder, depth-first and in a stable order."""
    videos: list[str] = []
    # onerror: one unreadable subfolder must not abort the whole scan.
    for root, dirnames, filenames in os.walk(folder, onerror=lambda _e: None):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if not name.startswith(".") and name.lower() not in SKIP_DIR_NAMES
        )
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            if Path(name).suffix.lower() not in VIDEO_EXTENSIONS:
                continue
            videos.append(os.path.join(root, name))
    return videos


class _Matcher:
    """Indexes the Movie, Series and Episode rows once, so a scan is a single pass over the database instead of a query per file."""

    def __init__(self, db: Session) -> None:
        self.movies_by_key: dict[tuple[str, int | None], Movie] = {}
        self.movies_by_title: dict[str, list[Movie]] = {}
        self.series_by_title: dict[str, Series] = {}
        self.episodes: dict[tuple[int, int, int], Episode] = {}

        # setdefault keeps the first row for a duplicate key, which keeps matching deterministic.
        for movie in db.query(Movie).all():
            self.movies_by_key.setdefault((_norm(movie.title), movie.year), movie)
            self.movies_by_title.setdefault(_norm(movie.title), []).append(movie)
        for series in db.query(Series).all():
            self.series_by_title.setdefault(_norm(series.title), series)
        for episode in db.query(Episode).all():
            self.episodes.setdefault(
                (episode.series_id, episode.season_number, episode.episode_number), episode
            )

    def movie(self, title: str, year: int | None) -> Movie | None:
        """Return the movie for this title and year, or a unique title match when the year is unknown."""
        exact = self.movies_by_key.get((_norm(title), year))
        if exact is not None:
            return exact
        if year is not None:
            return None
        # Only a single candidate counts: guessing between same-named movies would mis-file the file.
        candidates = self.movies_by_title.get(_norm(title), [])
        if len(candidates) == 1:
            return candidates[0]
        return None

    def series(self, title: str) -> Series | None:
        """Return the series whose title normalises to title."""
        return self.series_by_title.get(_norm(title))

    def episode(self, series_id: int, season: int, episode: int) -> Episode | None:
        """Return the episode row for this series, season and episode number."""
        return self.episodes.get((series_id, season, episode))


def _match(real_path: str, media_type: str, matcher: _Matcher) -> tuple[str | None, int | None]:
    """Return ("movie"|"episode", owner id) when the file is unambiguous, otherwise (None, None)."""
    name = Path(real_path).name
    if media_type == "movie":
        parsed = parse_movie(Path(name).stem)
        if parsed is None or parsed[1] is None:
            # The importer stores files as movies_root/"Title (Year)"/"Title (Year).ext",
            # so the containing folder often carries the year the file name left out.
            from_folder = parse_movie(Path(real_path).parent.name)
            if from_folder is not None and from_folder[1] is not None:
                parsed = from_folder
        if parsed is None:
            return None, None
        movie = matcher.movie(parsed[0], parsed[1])
        if movie is None:
            return None, None
        return "movie", movie.id

    if media_type == "tv":
        parent = Path(real_path).parent.name
        # A season folder ("Season 2") is not the series, so the series folder is its parent.
        if SEASON_DIR_RE.match(parent):
            series_folder = Path(real_path).parent.parent.name
        else:
            series_folder = parent
        series = matcher.series(series_folder)
        if series is None:
            return None, None
        parsed_episode = parse_episode(name)
        if parsed_episode is None:
            return None, None
        season, episode = parsed_episode
        # The file name's season is authoritative; the folder season only located the series folder.
        row = matcher.episode(series.id, int(season), int(episode))
        if row is None:
            return None, None
        return "episode", row.id

    return None, None


def scan(db: Session, now: datetime | None = None) -> dict:
    """One full pass over the library; the caller commits."""
    stamp = now or datetime.now(timezone.utc)
    matcher = _Matcher(db)
    existing: dict[str, MediaFile] = {_real(row.path): row for row in db.query(MediaFile).all()}
    seen: set[str] = set()
    added = updated = matched = unmatched = missing = 0

    for folder, media_type, root_folder_id in library_folders(db):
        for raw_path in walk_videos(folder):
            real = os.path.realpath(raw_path)
            key = _real(real)
            if key in seen:
                # The same file can be reachable from two folders, or recorded under two paths.
                continue
            seen.add(key)
            try:
                st = os.stat(real)
            except OSError:
                # The file vanished mid-scan; the next run will record it as missing.
                continue

            row = existing.get(key)
            if row is None:
                row = MediaFile(
                    media_type=media_type, path=real, added_at=stamp, last_seen_at=stamp
                )
                db.add(row)
                existing[key] = row
                added += 1
            else:
                updated += 1

            row.media_type = media_type
            row.root_folder_id = root_folder_id
            row.size = st.st_size
            row.mtime_ns = st.st_mtime_ns
            row.missing = False
            row.last_seen_at = stamp
            # Never blank a quality that was detected earlier.
            row.quality = row.quality or parse_quality(os.path.basename(real))

            owner, owner_id = _match(real, media_type, matcher)
            if owner == "movie":
                row.movie_id = owner_id
                row.episode_id = None
                row.matched = True
                matched += 1
            elif owner == "episode":
                row.movie_id = None
                row.episode_id = owner_id
                row.matched = True
                matched += 1
            else:
                # Unidentified: keep it with both owners NULL for a person to place later.
                row.movie_id = None
                row.episode_id = None
                row.matched = False
                unmatched += 1

    for key, row in existing.items():
        if key in seen or row.missing:
            continue
        # Never delete here: a missing row keeps the history of the file.
        row.missing = True
        missing += 1

    # Keep the legacy flags the library pages read in step with what the scan just recorded.
    synced = sync_presence_flags(db)

    log.info(
        "library scan: seen=%d added=%d updated=%d matched=%d unmatched=%d missing=%d flags=%d",
        len(seen),
        added,
        updated,
        matched,
        unmatched,
        missing,
        synced["changed"],
    )
    return {
        "added": added,
        "seen": len(seen),
        "updated": updated,
        "matched": matched,
        "unmatched": unmatched,
        "missing": missing,
        "flags_changed": synced["changed"],
    }


def record_imported(
    db: Session,
    path: str | None,
    media_type: str,
    *,
    movie_id: int | None = None,
    episode_id: int | None = None,
) -> None:
    """Record a file the importer just wrote, so playback finds it before the next scan
    (caller commits). Safe to call twice: a row for the same path is updated in place."""
    if not path:
        return
    real = os.path.realpath(str(path))
    stamp = datetime.now(timezone.utc)
    row = db.query(MediaFile).filter(MediaFile.path == real).one_or_none()
    if row is None:
        row = MediaFile(path=real, media_type=media_type, added_at=stamp, last_seen_at=stamp)
        db.add(row)
    try:
        st = os.stat(real)
    except OSError:
        # The import reported a path that is not there yet; the scan will fill this in later.
        size, mtime_ns = None, None
    else:
        size, mtime_ns = st.st_size, st.st_mtime_ns
    row.media_type = media_type
    row.movie_id = movie_id
    row.episode_id = episode_id
    row.matched = movie_id is not None or episode_id is not None
    row.missing = False
    row.size = size
    row.mtime_ns = mtime_ns
    row.quality = row.quality or parse_quality(os.path.basename(real))
    row.last_seen_at = stamp


def forget_movie_files(db: Session, movie_ids) -> None:
    """Delete media_files rows owned by these movies (caller commits)."""
    ids = list(movie_ids)
    if not ids:
        return
    db.query(MediaFile).filter(MediaFile.movie_id.in_(ids)).delete(synchronize_session=False)


def forget_episode_files(db: Session, episode_ids) -> None:
    """Delete media_files rows owned by these episodes (caller commits)."""
    ids = list(episode_ids)
    if not ids:
        return
    db.query(MediaFile).filter(MediaFile.episode_id.in_(ids)).delete(synchronize_session=False)


def file_counts(db: Session) -> dict:
    """How the library breaks down: every recorded file, how many are tied to a title, how many
    are not, and how many have gone from disk since the last scan."""
    rows = db.query(MediaFile).all()
    return {
        "total": len(rows),
        "matched": sum(1 for row in rows if row.matched),
        "unmatched": sum(1 for row in rows if not row.matched),
        "missing": sum(1 for row in rows if row.missing),
    }


def library_file_list(db: Session, show: str = "all", limit: int = 500) -> list[dict]:
    """The files an admin page lists, newest first. `show` narrows to "unmatched" or "missing";
    anything else lists everything. Owners are resolved in bulk rather than per row, and only a
    file's name is exposed, never its full path."""
    query = db.query(MediaFile)
    if show == "unmatched":
        query = query.filter(MediaFile.matched.is_(False))
    elif show == "missing":
        query = query.filter(MediaFile.missing.is_(True))
    rows = query.order_by(MediaFile.id.desc()).limit(limit).all()

    movie_titles = {m.id: m.title for m in db.query(Movie).all()}
    series_titles = {s.id: s.title for s in db.query(Series).all()}
    episodes = {e.id: e for e in db.query(Episode).all()}

    out: list[dict] = []
    for row in rows:
        if row.movie_id is not None:
            owner = movie_titles.get(row.movie_id, f"movie {row.movie_id}")
        elif row.episode_id is not None:
            episode = episodes.get(row.episode_id)
            if episode is None:
                owner = f"episode {row.episode_id}"
            else:
                label = series_titles.get(episode.series_id, "Series")
                owner = f"{label} - S{episode.season_number:02d}E{episode.episode_number:02d}"
        else:
            owner = ""
        out.append({
            "id": row.id,
            "name": os.path.basename(row.path),
            "owner": owner,
            "media_type": row.media_type,
            "quality": row.quality or "",
            "size": row.size or 0,
            "matched": row.matched,
            "missing": row.missing,
        })
    return out


def has_playable_file(db: Session, kind: str, item_id: int) -> bool:
    """True when this movie or episode has at least one recorded file that is still on disk.
    M50b reads this instead of the legacy Movie.has_file / Episode.has_file flag, which the
    scan does not maintain."""
    query = db.query(MediaFile).filter(MediaFile.missing.is_(False))
    query = query.filter(MediaFile.movie_id == item_id) if kind == "movie" else query.filter(MediaFile.episode_id == item_id)
    return bool(db.query(query.exists()).scalar())


def playable_ids(db: Session, kind: str, item_ids) -> set[int]:
    """Which of these movies or episodes have at least one recorded file still on disk.
    The bulk form of has_playable_file: one query for a whole season instead of one per episode."""
    ids = list(item_ids)
    if not ids:
        return set()
    column = MediaFile.movie_id if kind == "movie" else MediaFile.episode_id
    rows = db.query(column).filter(column.in_(ids), MediaFile.missing.is_(False)).distinct()
    return {row[0] for row in rows}


def sync_presence_flags(db: Session) -> dict:
    """Keep the legacy Movie.has_file and Episode.has_file flags in step with media_files.

    Playback and availability resolve media_files rows, but the library pages, the play buttons
    and the calendar still read these flags, so the scan maintains them as a derived cache
    instead of leaving them stale. The CALLER commits. Returns how many flags changed."""
    changed = 0

    movie_ids = [row[0] for row in db.query(Movie.id)]
    on_disk = playable_ids(db, "movie", movie_ids)
    for movie in db.query(Movie).all():
        wanted = movie.id in on_disk
        if bool(movie.has_file) != wanted:
            movie.has_file = wanted
            changed += 1

    episode_ids = [row[0] for row in db.query(Episode.id)]
    on_disk = playable_ids(db, "episode", episode_ids)
    for episode in db.query(Episode).all():
        wanted = episode.id in on_disk
        if bool(episode.has_file) != wanted:
            episode.has_file = wanted
            changed += 1

    return {"changed": changed}
