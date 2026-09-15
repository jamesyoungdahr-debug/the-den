"""P2 first slice - hand a file the browser cannot direct-play to ffmpeg.

A web <video> refuses HEVC, 10-bit H.264, HDR and Matroska outright, and nothing the server sends
changes that. The only fix is to produce a file it WILL take, in one of two shapes:

  * remux     - the streams are fine, the container is not (a .mkv holding H.264/AAC). ffmpeg
                copies them into MP4, which takes seconds and loses nothing.
  * transcode - a stream itself is the problem (HEVC, 10-bit, HDR). ffmpeg re-encodes to H.264,
                which is slow and lossy but the only thing a browser will accept.

This module only decides and builds the command line. Running the process and serving the result
belongs elsewhere. Full HLS with restart-on-seek is the rest of P2 and is not built yet."""

from __future__ import annotations

import logging
import os
import subprocess

from app import media_probe, playability

log = logging.getLogger(__name__)

# Streams every current browser plays. Anything outside these needs ffmpeg's help.
PLAYABLE_VIDEO = {"h264", "vp8", "vp9", "av1"}
PLAYABLE_AUDIO = {"aac", "mp3", "opus", "vorbis", "flac"}
# ffprobe's format_name for both MP4 and Matroska is a comma-separated list, so these are matched
# as whole names (see container_is_playable), never as substrings.
PLAYABLE_CONTAINERS = ("mov", "mp4")

# H.264 encoders, best first. VAAPI is the hardware path on the HoltOS laptop's Radeon; libx264 is
# the floor that always works.
VAAPI_DEVICE = "/dev/dri/renderD128"
_ENCODERS = (
    ("h264_vaapi", ["-vf", "format=nv12,hwupload", "-c:v", "h264_vaapi", "-qp", "22"]),
    ("libx264", ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21"]),
)

_detected: list[str] | None = None


def _lists_encoder(exe: str, name: str) -> bool:
    """True when this ffmpeg build advertises the encoder. Cheap and authoritative."""
    try:
        result = subprocess.run([exe, "-hide_banner", "-encoders"], capture_output=True, timeout=15, check=False, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return name.encode() in (result.stdout or b"")


def encoder_args() -> list[str]:
    """The best H.264 encoder this machine actually has, decided once and reused.

    VAAPI is only taken when its render device is present as well as advertised, because a build
    listing h264_vaapi on a machine with no card is exactly the case that would otherwise fail at
    the first frame."""
    global _detected
    if _detected is None:
        exe = media_probe.ffmpeg_path()
        chosen = ""
        if exe:
            for name, args in _ENCODERS:
                if name == "h264_vaapi" and not os.path.exists(VAAPI_DEVICE):
                    continue
                if _lists_encoder(exe, name):
                    _detected = list(args)
                    chosen = name
                    break
        if _detected is None:
            _detected = []
        log.info("transcode: encoder is %s", chosen or "none found")


    return list(_detected)


def container_is_playable(container: str | None, extension: str = "") -> bool:
    """Whether a browser will take this container as it stands.

    ffprobe reports WebM as "matroska,webm" -- the same family it gives a plain .mkv -- so the
    container name alone cannot tell them apart. The file's own extension can, and it has to:
    matching on the substring "webm" would call every MKV a WebM and skip the remux it needs."""
    names = {part.strip() for part in (container or "").lower().split(",") if part.strip()}
    if "matroska" in names or "webm" in names:
        return extension.lower() == ".webm"
    return bool(names & set(PLAYABLE_CONTAINERS))


def video_is_playable(video: dict | None) -> bool:
    """Whether a browser will take this video stream as it stands."""
    if not video:
        return True  # nothing known against it; let the browser try
    codec = (video.get("codec") or "").lower()
    if codec not in PLAYABLE_VIDEO:
        return False
    if codec == "h264" and (video.get("bit_depth") or 8) > 8:
        return False
    return (video.get("hdr") or "sdr").lower() == "sdr"


def audio_is_playable(audio: dict | None) -> bool:
    """Whether a browser will take this audio stream as it stands."""
    if not audio:
        return True  # no audio at all, or none we know about
    return (audio.get("codec") or "").lower() in PLAYABLE_AUDIO


def plan(summary: dict | None, extension: str = "") -> dict:
    """What has to happen before a browser plays this file (extension helps disambiguate Matroska).

    Returns {"mode", "reason", "video_copy", "audio_copy"} where mode is "direct" (nothing to do),
    "remux" (copy both streams into a new container) or "transcode" (the video must be re-encoded).
    """
    if not summary:
        # No probe data: let the browser try rather than re-encode something that may be fine.
        return {"mode": "direct", "reason": "no probe data", "video_copy": True, "audio_copy": True}

    video_ok = video_is_playable(summary.get("video"))
    audio_ok = audio_is_playable(playability.default_audio(summary))
    container_ok = container_is_playable(summary.get("container"), extension)

    if video_ok and audio_ok and container_ok:
        return {"mode": "direct", "reason": "the browser plays this as it is", "video_copy": True, "audio_copy": True}
    if video_ok and audio_ok:
        return {"mode": "remux", "reason": "the streams are fine but the container is not", "video_copy": True, "audio_copy": True}
    if video_ok:
        return {"mode": "remux", "reason": "only the audio needs re-encoding", "video_copy": True, "audio_copy": False}
    return {"mode": "transcode", "reason": "the video codec itself is not one a browser plays", "video_copy": False, "audio_copy": audio_ok}


def output_args(decided: dict, source: str, dest: str, start: int = 0) -> list[str]:
    """The ffmpeg argument list that writes dest. An argument list, never a shell string."""
    exe = media_probe.ffmpeg_path() or "ffmpeg"
    args = [exe, "-hide_banner", "-nostdin", "-y"]
    if decided.get("video_copy") is False and os.path.exists(VAAPI_DEVICE):
        args += ["-vaapi_device", VAAPI_DEVICE]
    if start > 0:
        args += ["-ss", str(start)]
    args += ["-i", source, "-map", "0:v:0", "-map", "0:a:0?"]
    if decided.get("video_copy"):
        args += ["-c:v", "copy"]
    else:
        args += encoder_args()
    if decided.get("audio_copy"):
        args += ["-c:a", "copy"]
    else:
        # downmix rather than plain -ac 2, which quietly folds surround into the front channels
        args += ["-c:a", "aac", "-b:a", "192k", "-ac", "2"]
    # Fast start so the browser can begin before the whole file has arrived, and an MP4 container
    # even when the source was something else.
    args += ["-movflags", "+faststart", dest]
    return args
