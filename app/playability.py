"""M49: can a web browser play a library file as it is? RFC 6381 codec strings for canPlayType, plus plain-language notes on what will stop direct play. Works on the summary dict from app.media_probe.summarise."""

from __future__ import annotations

import typing

H264_PROFILES = {
    "Constrained Baseline": "42E0",
    "Baseline": "4200",
    "Main": "4D00",
    "Extended": "5800",
    "High": "6400",
    "High 10": "6E00",
    "High 4:2:2": "7A00",
    "High 4:4:4 Predictive": "F400",
}

AUDIO_CODEC_STRINGS = {
    "aac": "mp4a.40.2",
    "mp3": "mp4a.6B",
    "opus": "opus",
    "vorbis": "vorbis",
    "flac": "flac",
    "ac3": "ac-3",
    "eac3": "ec-3",
    "alac": "alac",
}

BROWSER_VIDEO = {"h264", "hevc", "vp8", "vp9", "av1"}
BROWSER_AUDIO = {"aac", "mp3", "opus", "vorbis", "flac"}
SOME_BROWSERS_AUDIO = {"ac3", "eac3"}


def mime_type(container: str | None, extension: str) -> str:
    ext = extension.lower()
    c = (container or "").lower()
    if "mp4" in c or "mov" in c:
        return "video/mp4"
    if "matroska" in c or "webm" in c:
        return "video/webm" if ext == ".webm" else "video/x-matroska"
    if c == "avi":
        return "video/x-msvideo"
    if c == "mpegts":
        return "video/mp2t"
    fallback = {
        ".mp4": "video/mp4",
        ".m4v": "video/mp4",
        ".mov": "video/mp4",
        ".webm": "video/webm",
        ".mkv": "video/x-matroska",
    }
    return fallback.get(ext, "application/octet-stream")


def video_codec_string(video: dict | None) -> str | None:
    if video is None:
        return None
    codec = video.get("codec")
    level = video.get("level")
    depth = video.get("bit_depth") or 8

    if codec == "h264":
        pc = H264_PROFILES.get(video.get("profile") or "")
        if pc is None or not isinstance(level, int) or level <= 0:
            return None
        return f"avc1.{pc}{level:02X}"

    if codec == "hevc":
        if not isinstance(level, int) or level <= 0:
            return None
        profile = video.get("profile") or ""
        if profile == "Main":
            return f"hvc1.1.6.L{level}.B0"
        if profile == "Main 10":
            return f"hvc1.2.4.L{level}.B0"
        return None

    if codec == "vp9":
        return "vp09.02.10.10" if depth >= 10 else "vp09.00.10.08"

    if codec == "av1":
        return "av01.0.08M.10" if depth >= 10 else "av01.0.08M.08"

    if codec == "vp8":
        return "vp8"

    return None


def default_audio(summary: dict) -> dict | None:
    tracks = summary.get("audio") or []
    for track in tracks:
        if track.get("default", False):
            return track
    if tracks:
        return tracks[0]
    return None


def audio_codec_string(codec: str | None) -> str | None:
    return AUDIO_CODEC_STRINGS.get((codec or "").lower())


def browser_type(summary: dict, extension: str) -> str:
    mime = mime_type(summary.get("container"), extension)
    video_cs = video_codec_string(summary.get("video"))
    audio_track = default_audio(summary)
    audio_cs = audio_codec_string(audio_track.get("codec")) if audio_track else None
    codecs = [s for s in (video_cs, audio_cs) if s]

    # Only add codecs= when every present stream has a known string.
    if video_cs and (audio_track is None or audio_cs):
        return f'{mime}; codecs="{",".join(codecs)}"'
    return mime


def direct_play_notes(summary: dict) -> list[str]:
    notes = []
    c = (summary.get("container") or "").lower()
    v = summary.get("video")
    a = default_audio(summary)

    if c in ("avi", "mpegts"):
        notes.append(f"The {c} container does not play in web browsers.")

    if v:
        codec = (v.get("codec") or "").lower()
        if codec not in BROWSER_VIDEO:
            notes.append(f"Video codec {codec or 'unknown'} does not play in web browsers.")
        elif codec == "h264":
            bit_depth = v.get("bit_depth") or 8
            if bit_depth > 8:
                notes.append("10-bit H.264 does not play in web browsers.")
        elif codec == "hevc":
            notes.append("HEVC video plays only in browsers with hardware HEVC decoding.")

        hdr = v.get("hdr") or "sdr"
        if hdr != "sdr":
            notes.append("HDR video is shown without tone mapping, so colours may look washed out on SDR screens.")

    if a:
        ac = (a.get("codec") or "").lower()
        if ac in SOME_BROWSERS_AUDIO:
            notes.append(f"Audio codec {ac} plays only in some browsers.")
        elif ac not in BROWSER_AUDIO:
            notes.append(f"Audio codec {ac or 'unknown'} does not play in web browsers.")

    if len(summary.get("audio") or []) > 1:
        notes.append("Only the default audio track plays until transcoding arrives.")

    subs = summary.get("subtitles") or []
    if any(s.get("kind") == "image" for s in subs):
        notes.append("Picture-based subtitles (PGS or VobSub) can't be shown yet.")

    return notes