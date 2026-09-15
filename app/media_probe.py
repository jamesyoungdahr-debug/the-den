"""M49: run ffprobe on a library file once and keep a small summary of its streams.

ffprobe runs as a separate process with an argument list and a timeout, so a bad file can't crash
the server. Without ffprobe (FFPROBE unset and nothing on PATH) probe() returns None and playback
still works, just without codec details or embedded subtitles."""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import MediaProbe

log = logging.getLogger(__name__)

FFPROBE_TIMEOUT = 30
TEXT_SUBTITLE_CODECS: set[str] = {"subrip", "ass", "ssa", "mov_text", "webvtt", "text"}


def _tool_path(env_name: str, program: str) -> str | None:
    """Return an absolute path to *program*, preferring env var *env_name* if it points to an executable."""
    value = os.environ.get(env_name, "").strip()
    if value:
        return value if os.path.isfile(value) and os.access(value, os.X_OK) else None
    return shutil.which(program)


def ffprobe_path() -> str | None:
    """Locate the ffprobe executable."""
    return _tool_path("FFPROBE", "ffprobe")


def ffmpeg_path() -> str | None:
    """Locate the ffmpeg executable."""
    return _tool_path("FFMPEG", "ffmpeg")


def run_ffprobe(path: str) -> dict | None:
    """Run ffprobe on *path* and return the parsed JSON, or None on any failure."""
    exe = ffprobe_path()
    if not exe:
        return None

    cmd = [exe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", "-show_chapters", "-i", path]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=FFPROBE_TIMEOUT, check=False, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("ffprobe failed for %s: %s", path, exc)
        return None

    if result.returncode != 0:
        log.warning("ffprobe exited %s for %s: %s", result.returncode, path, result.stderr[:300].decode("utf-8", "replace"))
        return None

    try:
        data = json.loads(result.stdout)
    except ValueError:
        log.warning("ffprobe gave invalid JSON for %s", path)
        return None

    if not isinstance(data, dict):
        return None
    return data


def _int(value) -> int | None:
    """Coerce *value* to int via float, returning None on failure."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _ms(seconds) -> int | None:
    """Convert seconds (str or number) to milliseconds as an int, or None."""
    try:
        return round(float(seconds) * 1000)
    except (TypeError, ValueError):
        return None


def _tags(stream: dict) -> dict:
    """Return a lowercase-keyed copy of the stream's tags."""
    return {str(k).lower(): v for k, v in (stream.get("tags") or {}).items()}


def _flag(stream: dict, name: str) -> bool:
    """Return True when *name* is set in the stream's disposition map."""
    return bool((stream.get("disposition") or {}).get(name))


def _bit_depth(stream: dict) -> int:
    """Infer video bit depth from bits_per_raw_sample or pix_fmt, defaulting to 8."""
    raw = _int(stream.get("bits_per_raw_sample"))
    if raw and raw > 0:
        return raw
    pix = stream.get("pix_fmt") or ""
    if "12" in pix:
        return 12
    if "10" in pix:
        return 10
    return 8


def _hdr(stream: dict) -> str:
    """Return 'dv', 'hdr10', 'hlg' or 'sdr' based on side data and color transfer."""
    for side in stream.get("side_data_list") or []:
        kind = str(side.get("side_data_type") or "")
        if "DOVI" in kind or "Dolby Vision" in kind:
            return "dv"
    transfer = stream.get("color_transfer")
    if transfer == "smpte2084":
        return "hdr10"
    if transfer == "arib-std-b67":
        return "hlg"
    return "sdr"


def summarise(raw: dict, size: int) -> dict:
    """Build a compact summary dict from raw ffprobe JSON and the file *size*."""
    streams = raw.get("streams") or []
    fmt = raw.get("format") or {}

    video_stream = next((s for s in streams if s.get("codec_type") == "video" and not _flag(s, "attached_pic")), None)
    video: dict | None = None
    if video_stream is not None:
        level = _int(video_stream.get("level"))
        video = {
            "index": _int(video_stream.get("index")),
            "codec": video_stream.get("codec_name") or "",
            "profile": video_stream.get("profile"),
            "level": level if level and level > 0 else None,
            "pix_fmt": video_stream.get("pix_fmt"),
            "bit_depth": _bit_depth(video_stream),
            "width": _int(video_stream.get("width")),
            "height": _int(video_stream.get("height")),
            "hdr": _hdr(video_stream),
        }

    audio = [
        {
            "index": _int(s.get("index")),
            "codec": s.get("codec_name") or "",
            "channels": _int(s.get("channels")),
            "channel_layout": s.get("channel_layout"),
            "language": _tags(s).get("language"),
            "title": _tags(s).get("title"),
            "default": _flag(s, "default"),
        }
        for s in streams
        if s.get("codec_type") == "audio"
    ]

    subtitles = [
        {
            "index": _int(s.get("index")),
            "codec": s.get("codec_name") or "",
            "language": _tags(s).get("language"),
            "title": _tags(s).get("title"),
            "default": _flag(s, "default"),
            "forced": _flag(s, "forced"),
            "kind": "text" if (s.get("codec_name") or "") in TEXT_SUBTITLE_CODECS else "image",
        }
        for s in streams
        if s.get("codec_type") == "subtitle"
    ]

    chapters = [
        {
            "start_ms": _ms(c.get("start_time")),
            "end_ms": _ms(c.get("end_time")),
            "title": _tags(c).get("title"),
        }
        for c in raw.get("chapters") or []
    ]

    return {
        "container": fmt.get("format_name") or "",
        "duration_ms": _ms(fmt.get("duration")),
        "bit_rate": _int(fmt.get("bit_rate")),
        "size": size,
        "video": video,
        "audio": audio,
        "subtitles": subtitles,
        "chapters": chapters,
    }


def probe(db: Session, path: str) -> dict | None:
    """The summary for a real library path (already checked by app.media_stream), from the cache when the file's size and mtime still match, else by running ffprobe."""
    try:
        st = os.stat(path)
    except OSError:
        return None

    row = db.query(MediaProbe).filter(MediaProbe.file_path == path).first()
    if row is not None and row.size == st.st_size and row.mtime_ns == st.st_mtime_ns:
        try:
            return json.loads(row.summary)
        except ValueError:
            pass

    raw = run_ffprobe(path)
    if raw is None:
        return None

    summary = summarise(raw, st.st_size)

    if row is None:
        row = MediaProbe(file_path=path)
        db.add(row)

    row.size = st.st_size
    row.mtime_ns = st.st_mtime_ns
    row.probed_at = datetime.now(timezone.utc)
    row.summary = json.dumps(summary)
    db.commit()

    return summary
