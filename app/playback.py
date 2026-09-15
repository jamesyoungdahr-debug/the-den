"""M49: where each user is in each movie and episode, and whether they've watched it.

Rules: positions are clamped to the duration; past 90 per cent an item counts as played and its resume point is cleared; a resume point under 60 seconds is dropped; play_count rises when an item becomes played. SQLite reuses the highest row id, so the delete paths call forget_items / forget_user."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import Episode, Movie, PlaybackState, Series


KINDS = ("movie", "episode")
EVENTS = ("start", "progress", "pause", "seek", "stop")
PLAYED_FRACTION = 0.9
MIN_RESUME_MS = 60_000
MAX_DURATION_MS = 48 * 3600 * 1000


def _now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def _as_ms(value, name: str) -> int:
    """Convert a numeric value to milliseconds, raising on invalid input."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} must be a number")
    return int(round(value))


def get_state(db: Session, user_id: int, kind: str, item_id: int) -> PlaybackState | None:
    """Return the playback state for a user/item pair, or None."""
    return (
        db.query(PlaybackState)
        .filter(
            PlaybackState.user_id == user_id,
            PlaybackState.item_kind == kind,
            PlaybackState.item_id == item_id,
        )
        .first()
    )


def _get_or_create(db: Session, user_id: int, kind: str, item_id: int) -> PlaybackState:
    """Return an existing state or create a new one."""
    if kind not in KINDS:
        raise ValueError("unknown item kind")
    state = get_state(db, user_id, kind, item_id)
    if state is None:
        state = PlaybackState(
            user_id=user_id,
            item_kind=kind,
            item_id=item_id,
            position_ms=0,
            duration_ms=0,
            played=False,
            play_count=0,
            updated_at=_now(),
        )
        db.add(state)
    return state


def record_progress(
    db: Session,
    user_id: int,
    kind: str,
    item_id: int,
    position_ms,
    duration_ms,
    event: str,
    device: str | None = None,
) -> PlaybackState:
    """Record a playback progress update and return the resulting state."""
    if event not in EVENTS:
        raise ValueError("unknown event")
    position = _as_ms(position_ms, "position_ms")
    duration = _as_ms(duration_ms, "duration_ms")
    if position < 0 or duration < 0:
        raise ValueError("negative time")
    duration = min(duration, MAX_DURATION_MS)
    state = _get_or_create(db, user_id, kind, item_id)
    if duration > 0:
        state.duration_ms = duration
    if state.duration_ms > 0:
        position = min(position, state.duration_ms)
    if state.duration_ms > 0 and position >= state.duration_ms * PLAYED_FRACTION:
        if not state.played:
            state.play_count = (state.play_count or 0) + 1
        state.played = True
        state.position_ms = 0
    else:
        state.position_ms = position if position >= MIN_RESUME_MS else 0
    now = _now()
    state.last_played_at = now
    state.updated_at = now
    if device:
        state.device = device[:100]
    db.commit()
    return state


def set_watched(
    db: Session, user_id: int, kind: str, item_id: int, played: bool
) -> PlaybackState:
    """Explicitly mark an item as watched or unwatched."""
    state = _get_or_create(db, user_id, kind, item_id)
    if played and not state.played:
        state.play_count = (state.play_count or 0) + 1
    state.played = bool(played)
    state.position_ms = 0
    state.updated_at = _now()
    db.commit()
    return state


def states_for(
    db: Session, user_id: int, kind: str, item_ids
) -> dict[int, PlaybackState]:
    """Return a mapping of item_id to PlaybackState for the given ids."""
    ids = list(item_ids)
    if not ids:
        return {}
    return {
        s.item_id: s
        for s in db.query(PlaybackState).filter(
            PlaybackState.user_id == user_id,
            PlaybackState.item_kind == kind,
            PlaybackState.item_id.in_(ids),
        )
    }


def state_dict(state: PlaybackState | None) -> dict:
    """Return a serialisable dict for a playback state (or defaults if None)."""
    if state is None:
        return {
            "position_ms": 0,
            "duration_ms": 0,
            "played": False,
            "play_count": 0,
            "last_played_at": None,
            "progress": 0.0,
        }
    progress = (
        round(state.position_ms / state.duration_ms, 3)
        if state.duration_ms
        else 0.0
    )
    return {
        "position_ms": state.position_ms,
        "duration_ms": state.duration_ms,
        "played": state.played,
        "play_count": state.play_count,
        "last_played_at": state.last_played_at.isoformat() if state.last_played_at else None,
        "progress": progress,
    }


def continue_watching(
    db: Session, user_id: int, limit: int = 20
) -> list[dict]:
    """Return up to *limit* items the user has an active resume point for."""
    rows = (
        db.query(PlaybackState)
        .filter(
            PlaybackState.user_id == user_id,
            PlaybackState.position_ms > 0,
        )
        .order_by(PlaybackState.updated_at.desc())
        .limit(limit * 2)
        .all()
    )
    out: list[dict] = []
    for state in rows:
        if state.item_kind == "movie":
            movie = db.get(Movie, state.item_id)
            if movie is None or not movie.has_file:
                continue
            title = movie.title
            subtitle = str(movie.year) if movie.year else ""
            poster_path = movie.poster_path or ""
        elif state.item_kind == "episode":
            ep = db.get(Episode, state.item_id)
            if ep is None or not ep.has_file:
                continue
            series = db.get(Series, ep.series_id)
            title = series.title if series else "Episode"
            subtitle = f"S{ep.season_number:02d}E{ep.episode_number:02d}" + (
                f" · {ep.title}" if ep.title else ""
            )
            poster_path = (series.poster_path or "") if series else ""
        else:
            continue
        out.append(
            {
                "kind": state.item_kind,
                "id": state.item_id,
                "title": title,
                "subtitle": subtitle,
                "poster_path": poster_path,
                "href": f"/watch/{state.item_kind}/{state.item_id}",
                **state_dict(state),
            }
        )
        if len(out) == limit:
            break
    return out


def next_episode(db: Session, episode: Episode) -> Episode | None:
    """Return the next watchable episode in the same series, or None."""
    return (
        db.query(Episode)
        .filter(
            Episode.series_id == episode.series_id,
            Episode.has_file.is_(True),
            or_(
                Episode.season_number > episode.season_number,
                and_(
                    Episode.season_number == episode.season_number,
                    Episode.episode_number > episode.episode_number,
                ),
            ),
        )
        .order_by(Episode.season_number, Episode.episode_number)
        .first()
    )


def forget_items(db: Session, kind: str, item_ids) -> None:
    """Delete playback rows for the given items (caller commits)."""
    ids = list(item_ids)
    if not ids:
        return
    db.query(PlaybackState).filter(
        PlaybackState.item_kind == kind,
        PlaybackState.item_id.in_(ids),
    ).delete(synchronize_session=False)


def forget_user(db: Session, user_id: int) -> None:
    """Delete all playback rows for a user (caller commits)."""
    db.query(PlaybackState).filter(
        PlaybackState.user_id == user_id,
    ).delete(synchronize_session=False)
