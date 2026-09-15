"""M49: subtitle tracks for the web player, served as WebVTT.

Sidecar files are found and read only through app.media_stream (track ids, never file names).
Embedded text tracks come from the probe summary."""

from __future__ import annotations

import logging
import os
import re
import subprocess

from fastapi import HTTPException

from app import media_probe, media_stream

log = logging.getLogger(__name__)
EMBEDDED_TIMEOUT = 120
_EMBEDDED_ID = re.compile(r"e\d{1,4}")

LANGUAGE_RE = re.compile(r"[a-z]{2,3}(-[a-z0-9]{2,8})?")
MARKERS = {"forced", "sdh", "cc", "hi"}
_TIMESTAMP = re.compile(r"\b(\d{1,3}):(\d{2}):(\d{2})[,.](\d{3})\b")
_ASS_TAG = re.compile(r"\{\\[^}]*\}")


def parse_tail(tail: str) -> dict:
    parts = [p for p in tail.lower().split(".") if p]
    language = next((p for p in parts if p not in MARKERS and LANGUAGE_RE.fullmatch(p)), None)
    return {"language": language, "forced": "forced" in parts, "sdh": any(p in parts for p in ("sdh", "cc", "hi"))}


def track_label(language: str | None, title: str | None = None, forced: bool = False, sdh: bool = False) -> str:
    label = title or (language.upper() if language else "Unknown")
    if forced:
        label += " (forced)"
    if sdh:
        label += " (SDH)"
    return label


def _fix_timestamp(match: re.Match) -> str:
    hours, minutes, seconds, millis = match.groups()
    return f"{int(hours):02d}:{minutes}:{seconds}.{millis}"


def srt_to_webvtt(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.lstrip().startswith("WEBVTT"):
        return text if text.endswith("\n") else text + "\n"
    text = _TIMESTAMP.sub(_fix_timestamp, text)
    text = _ASS_TAG.sub("", text)
    return "WEBVTT\n\n" + text.strip() + "\n"


def sidecar_track_list(library_file) -> list[dict]:
    tracks = []
    for track in media_stream.sidecar_tracks(library_file):
        meta = parse_tail(track["tail"])
        tracks.append(
            {
                "id": track["id"],
                "source": "sidecar",
                "language": meta["language"],
                "label": track_label(meta["language"], None, meta["forced"], meta["sdh"]),
                "forced": meta["forced"],
                "default": False,
            }
        )
    return tracks


def embedded_track_lists(summary: dict | None) -> tuple[list[dict], list[str]]:
    """(playable text tracks, labels of picture-based tracks that can't be shown yet)."""
    playable, unavailable = [], []
    for s in (summary or {}).get("subtitles") or []:
        index = s.get("index")
        if index is None:
            continue
        label = track_label(s.get("language"), s.get("title"), bool(s.get("forced")), False)
        if s.get("kind") == "text":
            playable.append(
                {
                    "id": f"e{index}",
                    "source": "embedded",
                    "language": s.get("language"),
                    "label": label,
                    "forced": bool(s.get("forced")),
                    "default": bool(s.get("default")),
                }
            )
        else:
            unavailable.append(label)
    return playable, unavailable


def webvtt_for_sidecar(library_file, track_id: str) -> str:
    track = media_stream.resolve_sidecar(library_file, track_id)
    return srt_to_webvtt(media_stream.read_sidecar_bytes(track))


def webvtt_for_embedded(library_file, summary: dict | None, track_id: str) -> str:
    """An embedded text subtitle track as WebVTT, extracted once with ffmpeg and cached under a hash-named file."""
    if not _EMBEDDED_ID.fullmatch(track_id):
        raise HTTPException(404, "Subtitle track not found")
    index = int(track_id[1:])
    stream = next((s for s in (summary or {}).get("subtitles") or [] if s.get("index") == index and s.get("kind") == "text"), None)
    if stream is None:
        raise HTTPException(404, "Subtitle track not found")
    cache = media_stream.subtitle_cache_path(library_file, index)
    if cache.is_file():
        return cache.read_text(encoding="utf-8")
    exe = media_probe.ffmpeg_path()
    if not exe:
        raise HTTPException(404, "ffmpeg is not installed on the server")
    cmd = [exe, "-nostdin", "-v", "error", "-i", library_file.path, "-map", f"0:{index}", "-c:s", "webvtt", "-f", "webvtt", "pipe:1"]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=EMBEDDED_TIMEOUT, check=False, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("subtitle extraction failed for %s stream %s: %s", library_file.path, index, exc)
        raise HTTPException(502, "Couldn't extract that subtitle track")
    text = result.stdout.decode("utf-8", "replace")
    if result.returncode != 0 or not text.lstrip().startswith("WEBVTT"):
        log.warning("ffmpeg exited %s extracting %s stream %s: %s", result.returncode, library_file.path, index, result.stderr[:300].decode("utf-8", "replace"))
        raise HTTPException(502, "Couldn't extract that subtitle track")
    temporary = cache.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, cache)
    return text