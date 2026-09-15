"""M49: direct play API. Play info, the file itself with byte ranges, WebVTT subtitles, progress and watched state.

Every route needs a signed-in user (session cookie or X-Api-Key). Files are only ever opened through app.media_stream, never here."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth, media_probe, media_stream, playability, playback, subtitle_tracks
from app.deps import get_db
from app.models import Episode, Movie, Series, User

router = APIRouter(prefix="/api/play", tags=["play"])
Kind = Literal["movie", "episode"]
_TRACK_ID = re.compile(r"[xe]\d{1,4}")


class ProgressBody(BaseModel):
    position_ms: float
    duration_ms: float = 0
    event: str = "progress"
    device: str | None = None


class WatchedBody(BaseModel):
    played: bool


def _episode_label(episode: Episode) -> str:
    return f"S{episode.season_number:02d}E{episode.episode_number:02d}" + (f" · {episode.title}" if episode.title else "")


def item_meta(db: Session, kind: str, item_id: int) -> dict:
    """Title, subtitle, poster and back link for a movie or episode; 404 when it doesn't exist."""
    if kind == "movie":
        movie = db.get(Movie, item_id)
        if movie is None: raise HTTPException(404, "Item not found")
        return {"title": movie.title, "subtitle": str(movie.year) if movie.year else "", "poster_path": movie.poster_path or "", "back_href": "/library"}
    episode = db.get(Episode, item_id)
    if episode is None: raise HTTPException(404, "Item not found")
    series = db.get(Series, episode.series_id)
    return {"title": series.title if series else "Episode", "subtitle": _episode_label(episode), "poster_path": (series.poster_path or "") if series else "", "back_href": f"/ui/series/{episode.series_id}"}


@router.get("/continue")
def continue_watching(user: User = Depends(auth.require_user), db: Session = Depends(get_db)):
    return {"items": playback.continue_watching(db, user.id)}


@router.get("/{kind}/{item_id}")
def play_info(kind: Kind, item_id: int, user: User = Depends(auth.require_user), db: Session = Depends(get_db)):
    meta = item_meta(db, kind, item_id)
    library_file = media_stream.resolve_item_file(db, kind, item_id)
    summary = media_probe.probe(db, library_file.path)
    extension = Path(library_file.path).suffix.lower()
    base = f"/api/play/{kind}/{item_id}"
    sidecars = subtitle_tracks.sidecar_track_list(library_file)
    embedded, unavailable = subtitle_tracks.embedded_track_lists(summary)
    if not media_probe.ffmpeg_path():
        embedded = []
    if summary is not None:
        notes = playability.direct_play_notes(summary)
        media_type = playability.browser_type(summary, extension)
    else:
        notes = ["Codec details are unavailable because ffprobe isn't installed on the server." if not media_probe.ffprobe_path() else "The server couldn't read this file's codec details."]
        media_type = library_file.content_type
    next_item = None
    if kind == "episode":
        following = playback.next_episode(db, db.get(Episode, item_id))
        if following is not None:
            next_item = {"id": following.id, "label": _episode_label(following), "href": f"/watch/episode/{following.id}"}
    return {
        "kind": kind, "id": item_id, **meta,
        "stream_url": f"{base}/file?file_id={library_file.file_id}" if library_file.file_id is not None else f"{base}/file",
        "files": media_stream.file_choices(db, kind, item_id), "file_id": library_file.file_id,
        "type": media_type, "probed": summary is not None,
        "duration_ms": summary.get("duration_ms") if summary else None,
        "video": summary.get("video") if summary else None,
        "audio": summary.get("audio", []) if summary else [],
        "chapters": summary.get("chapters", []) if summary else [],
        "notes": notes,
        "subtitles": [{**track, "url": f"{base}/subtitles/{track['id']}.vtt"} for track in sidecars + embedded],
        "unavailable_subtitles": unavailable,
        "state": playback.state_dict(playback.get_state(db, user.id, kind, item_id)),
        "next": next_item,
    }


@router.api_route("/{kind}/{item_id}/file", methods=["GET", "HEAD"])
def play_file(kind: Kind, item_id: int, request: Request, file_id: int | None = None, user: User = Depends(auth.require_user), db: Session = Depends(get_db)):
    return media_stream.file_response(request, media_stream.resolve_item_file(db, kind, item_id, file_id))


@router.get("/{kind}/{item_id}/subtitles/{track_id}.vtt")
def play_subtitle(kind: Kind, item_id: int, track_id: str, file_id: int | None = None, user: User = Depends(auth.require_user), db: Session = Depends(get_db)):
    if not _TRACK_ID.fullmatch(track_id):
        raise HTTPException(404, "Subtitle track not found")
    library_file = media_stream.resolve_item_file(db, kind, item_id, file_id)
    if track_id.startswith("x"):
        text = subtitle_tracks.webvtt_for_sidecar(library_file, track_id)
    else:
        text = subtitle_tracks.webvtt_for_embedded(library_file, media_probe.probe(db, library_file.path), track_id)
    return Response(text, media_type="text/vtt; charset=utf-8", headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"})


@router.post("/{kind}/{item_id}/progress")
def play_progress(kind: Kind, item_id: int, body: ProgressBody, user: User = Depends(auth.require_user), db: Session = Depends(get_db)):
    media_stream.resolve_item_file(db, kind, item_id)  # only items with a playable file record progress
    try:
        state = playback.record_progress(db, user.id, kind, item_id, body.position_ms, body.duration_ms, body.event, body.device)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return playback.state_dict(state)


@router.post("/{kind}/{item_id}/watched")
def play_watched(kind: Kind, item_id: int, body: WatchedBody, user: User = Depends(auth.require_user), db: Session = Depends(get_db)):
    item_meta(db, kind, item_id)
    return playback.state_dict(playback.set_watched(db, user.id, kind, item_id, body.played))
