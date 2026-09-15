"""M49: the one place library files are opened for playback.

Security-sensitive (written by Claude). Every route that sends library bytes goes through here:
  * an item id is resolved to the path the importer stored, never a path from the request;
  * the real path (symlinks resolved) must sit inside a configured library folder, compared by
    whole path components, and no configured folders means nothing plays;
  * only video extensions are served, the file must be a regular file, and it is checked again
    with fstat after opening, so a file swapped between the check and the open is caught;
  * subtitle sidecars are addressed by track id, and symlinked sidecars are skipped;
  * cache file names come from a hash, never from anything in the URL.

Byte ranges are handled here because Starlette 0.38's FileResponse has no Range support.
"""

from __future__ import annotations

import email.utils
import hashlib
import logging
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

import anyio
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from starlette.responses import Response, StreamingResponse

from app import config
from app import settings as settings_module
from app.models import Episode, Movie, RootFolder

log = logging.getLogger(__name__)

KINDS = ("movie", "episode")
VIDEO_TYPES = {
    ".mkv": "video/x-matroska",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/mp4",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".ts": "video/mp2t",
    ".m2ts": "video/mp2t",
}
SIDECAR_EXTENSIONS = (".srt", ".vtt")
CHUNK_SIZE = 1024 * 1024
# At most 18 digits: no real offset is longer, and it keeps int() clear of Python's digit limit.
_RANGE = re.compile(r"^bytes=(\d{0,18})-(\d{0,18})$")


class RangeNotSatisfiable(Exception):
    pass


@dataclass(frozen=True)
class LibraryFile:
    kind: str
    item_id: int
    path: str  # real path, symlinks resolved
    content_type: str
    device: int = -1  # st_dev and st_ino when checked: the file opened later must be the same one
    inode: int = -1


# ---- which folders may be served ------------------------------------------------------

def _norm(path: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.expanduser(path)))


def allowed_roots(db: Session) -> list[str]:
    """Real paths of every configured library folder that exists: root folders plus the
    movies and TV roots from Settings. The download folder is deliberately not included."""
    effective = settings_module.effective(db)
    candidates = [r.path for r in db.query(RootFolder).all()] + [effective.movies_root, effective.tv_root]
    roots: list[str] = []
    for candidate in candidates:
        if not candidate or not str(candidate).strip():
            continue
        real = _norm(str(candidate))
        if os.path.isdir(real) and real not in roots:
            roots.append(real)
    return roots


def is_inside(path: str, roots: list[str]) -> bool:
    """True when the real path is one of the roots or below one, by whole path components
    (so /media-evil is not inside /media)."""
    real = _norm(path)
    for root in roots:
        try:
            if os.path.commonpath([real, root]) == root:
                return True
        except ValueError:  # different drives on Windows
            continue
    return False


# ---- item id to file -----------------------------------------------------------------

def _not_found(kind: str, item_id: int, why: str) -> HTTPException:
    log.warning("playback refused for %s %s: %s", kind, item_id, why)
    return HTTPException(404, "No playable file for this item")


def resolve_item_file(db: Session, kind: str, item_id: int) -> LibraryFile:
    if kind not in KINDS:
        raise HTTPException(404, "Unknown item kind")
    item = db.get(Movie if kind == "movie" else Episode, item_id)
    if item is None:
        raise HTTPException(404, "Item not found")
    raw = item.file_path
    if not item.has_file or not raw:
        raise HTTPException(404, "No file for this item")
    if not os.path.isabs(raw):
        raise _not_found(kind, item_id, "stored path is not absolute")
    real = os.path.realpath(raw)
    content_type = VIDEO_TYPES.get(Path(real).suffix.lower())
    if content_type is None:
        raise _not_found(kind, item_id, "not a video file extension")
    roots = allowed_roots(db)
    if not roots:
        raise _not_found(kind, item_id, "no library folders are configured")
    if not is_inside(real, roots):
        raise _not_found(kind, item_id, "file is outside every library folder")
    try:
        st = os.stat(real)
    except OSError:
        raise _not_found(kind, item_id, "file is missing")
    if not stat.S_ISREG(st.st_mode):
        raise _not_found(kind, item_id, "not a regular file")
    return LibraryFile(kind=kind, item_id=item_id, path=real, content_type=content_type, device=st.st_dev, inode=st.st_ino)


# ---- subtitle sidecars ---------------------------------------------------------------

def sidecar_tracks(library_file: LibraryFile) -> list[dict]:
    """Subtitle files next to the video named "<stem>.<anything>.srt|.vtt", in name order.
    Each gets a stable id ("x0", "x1", ...) and the middle part of its name ("en", "en.forced")
    for the caller to read a language from. Symlinks and non-files are skipped."""
    folder, name = os.path.split(library_file.path)
    stem = os.path.splitext(name)[0]
    prefix = stem + "."
    found: list[tuple[str, str]] = []
    try:
        with os.scandir(folder) as entries:
            for entry in entries:
                lower = entry.name.lower()
                if not entry.name.startswith(prefix) or not lower.endswith(SIDECAR_EXTENSIONS):
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                found.append((entry.name, entry.path))
    except OSError:
        return []
    tracks = []
    for index, (entry_name, entry_path) in enumerate(sorted(found)):
        base, extension = os.path.splitext(entry_name)
        tracks.append({
            "id": f"x{index}",
            "path": entry_path,
            "tail": base[len(prefix):],
            "format": extension.lower().lstrip("."),
        })
    return tracks


def resolve_sidecar(library_file: LibraryFile, track_id: str) -> dict:
    for track in sidecar_tracks(library_file):
        if track["id"] == track_id:
            return track
    raise HTTPException(404, "Subtitle track not found")


def read_sidecar_bytes(track: dict, limit: int = 5 * 1024 * 1024) -> bytes:
    """A sidecar's bytes, refusing symlinks, non-files and anything over `limit`."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(track["path"], flags)
    except OSError:
        raise HTTPException(404, "Subtitle track not found")
    with os.fdopen(fd, "rb") as handle:
        st = os.fstat(handle.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
            raise HTTPException(404, "Subtitle track not found")
        return handle.read(limit + 1)[:limit]


def subtitle_cache_path(library_file: LibraryFile, stream_index: int) -> Path:
    """Where an embedded subtitle converted to WebVTT is cached: the name is a hash of the file's
    real path, its mtime and the stream index, so a replaced file gets a fresh entry."""
    mtime_ns = os.stat(library_file.path).st_mtime_ns
    digest = hashlib.sha256(f"{library_file.path}\0{mtime_ns}\0{int(stream_index)}".encode()).hexdigest()
    folder = Path(config.STATE_DIR) / "media-cache" / "subtitles"
    folder.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(folder, 0o700)
    except OSError:
        pass
    return folder / f"{digest}.vtt"


# ---- byte ranges ---------------------------------------------------------------------

def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """The inclusive (start, end) of a single byte range, or None to send the whole file.
    Raises RangeNotSatisfiable for a valid range that lies outside the file. Headers this
    doesn't understand (other units, several ranges, bad syntax) are ignored, as RFC 9110 allows."""
    if not header:
        return None
    spec = header.strip()
    if "," in spec:
        return None
    match = _RANGE.match(spec)
    if not match:
        return None
    first, last = match.groups()
    if first == "" and last == "":
        return None
    if first == "":
        suffix = int(last)
        if suffix == 0 or size == 0:
            raise RangeNotSatisfiable()
        return max(0, size - suffix), size - 1
    start = int(first)
    if last != "" and int(last) < start:
        return None
    if start >= size:
        raise RangeNotSatisfiable()
    end = size - 1 if last == "" else min(int(last), size - 1)
    return start, end


def _validators(st: os.stat_result) -> tuple[str, str]:
    etag = f'"{st.st_size:x}-{st.st_mtime_ns:x}"'
    last_modified = email.utils.formatdate(st.st_mtime_ns / 1e9, usegmt=True)
    return etag, last_modified


def file_response(request: Request, library_file: LibraryFile) -> Response:
    """Send a resolved library file, honouring a single Range and If-Range. HEAD gets headers only."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(library_file.path, flags)
    except OSError:
        raise _not_found(library_file.kind, library_file.item_id, "file could not be opened")
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise _not_found(library_file.kind, library_file.item_id, "opened file is not a regular file")
        if library_file.inode != -1 and (st.st_dev, st.st_ino) != (library_file.device, library_file.inode):
            # a folder on the checked path was swapped between the check and the open
            raise _not_found(library_file.kind, library_file.item_id, "file changed after it was checked")
    except BaseException:
        os.close(fd)
        raise

    size = st.st_size
    etag, last_modified = _validators(st)
    headers = {
        "Accept-Ranges": "bytes",
        "ETag": etag,
        "Last-Modified": last_modified,
        "Cache-Control": "private, max-age=0, must-revalidate",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": "inline",
    }

    range_header = request.headers.get("range")
    if_range = request.headers.get("if-range")
    if range_header and if_range and if_range.strip() not in (etag, last_modified):
        range_header = None  # the client's copy is stale: send the whole current file

    try:
        byte_range = parse_range(range_header, size)
    except RangeNotSatisfiable:
        os.close(fd)
        return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{size}"})

    if byte_range is None:
        status, start, length = 200, 0, size
    else:
        start, end = byte_range
        status, length = 206, end - start + 1
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    headers["Content-Length"] = str(length)

    if request.method == "HEAD":
        os.close(fd)
        return Response(status_code=status, headers=headers, media_type=library_file.content_type)

    handle = os.fdopen(fd, "rb")

    async def body() -> AsyncIterator[bytes]:
        try:
            await anyio.to_thread.run_sync(handle.seek, start)
            remaining = length
            while remaining > 0:
                chunk = await anyio.to_thread.run_sync(handle.read, min(CHUNK_SIZE, remaining))
                if not chunk:
                    break  # the file shrank while streaming; stop rather than pad
                remaining -= len(chunk)
                yield chunk
        finally:
            handle.close()

    return StreamingResponse(body(), status_code=status, headers=headers, media_type=library_file.content_type)
