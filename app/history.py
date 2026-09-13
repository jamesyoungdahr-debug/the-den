"""Per-title event history (E5): every grab, import, upgrade, failure and removal,
timestamped, so a title's detail page can show what happened to it."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Episode, HistoryEvent


def record(
    db: Session, event: str, release_title: str, *,
    movie_id: int | None = None, episode_id: int | None = None,
    series_id: int | None = None, season_number: int | None = None,
    message: str = "",
) -> HistoryEvent:
    """Adds one history row. Commits."""
    row = HistoryEvent(
        event=event, release_title=release_title, message=message or None,
        movie_id=movie_id, episode_id=episode_id, series_id=series_id, season_number=season_number,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def for_movie(db: Session, movie_id: int, limit: int = 50) -> list[HistoryEvent]:
    return (
        db.query(HistoryEvent)
        .filter(HistoryEvent.movie_id == movie_id)
        .order_by(HistoryEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def for_episode(db: Session, episode_id: int, limit: int = 50) -> list[HistoryEvent]:
    return (
        db.query(HistoryEvent)
        .filter(HistoryEvent.episode_id == episode_id)
        .order_by(HistoryEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def for_series(db: Session, series_id: int, limit: int = 50) -> list[HistoryEvent]:
    """Season-pack events (series_id set directly) plus every one of the series's own episodes' events."""
    episode_ids = [row[0] for row in db.query(Episode.id).filter(Episode.series_id == series_id)]
    conditions = [HistoryEvent.series_id == series_id]
    if episode_ids:
        conditions.append(HistoryEvent.episode_id.in_(episode_ids))
    return (
        db.query(HistoryEvent)
        .filter(or_(*conditions))
        .order_by(HistoryEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def as_dicts(rows: list[HistoryEvent]) -> list[dict]:
    """The JSON shape used by the Detail payload and the web template."""
    return [
        {
            "event": r.event, "message": r.message, "release_title": r.release_title,
            "season_number": r.season_number, "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]