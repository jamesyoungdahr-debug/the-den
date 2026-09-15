"""M51: The Den's own watchlist -- a title somebody wants, kept here rather than in Plex.

Plex's Discover watchlist was the only one people had, which is a problem once Plex is removed.
This is the same idea owned locally, so an import list can pick it up on a schedule exactly as it
picked up the Plex one.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import WatchlistItem

KINDS = ("movie", "tv")


def for_user(db: Session, user_id: int) -> list[WatchlistItem]:
    """Everything on this person's watchlist, newest first."""
    return (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user_id)
        .order_by(WatchlistItem.added_at.desc(), WatchlistItem.id.desc())
        .all()
    )


def _row(db: Session, user_id: int, media_type: str, tmdb_id: int) -> WatchlistItem | None:
    return (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user_id, WatchlistItem.media_type == media_type, WatchlistItem.tmdb_id == tmdb_id)
        .first()
    )


def has(db: Session, user_id: int, media_type: str, tmdb_id: int) -> bool:
    return _row(db, user_id, media_type, tmdb_id) is not None


def add(db: Session, user_id: int, media_type: str, tmdb_id: int, title: str, year: int | None = None, poster_path: str | None = None) -> WatchlistItem | None:
    """Put a title on the list, or return the row already there.

    Idempotent on purpose: a double click or a retried request must not produce two rows for the
    same film. Returns None for a media type this table does not hold, rather than storing junk."""
    if media_type not in KINDS or not tmdb_id or not (title or "").strip():
        return None
    existing = _row(db, user_id, media_type, tmdb_id)
    if existing is not None:
        return existing
    row = WatchlistItem(user_id=user_id, media_type=media_type, tmdb_id=int(tmdb_id), title=title.strip()[:300], year=year, poster_path=poster_path or None)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def remove(db: Session, user_id: int, media_type: str, tmdb_id: int) -> bool:
    """Take a title off the list. True when something was there, so the caller can say so."""
    deleted = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user_id, WatchlistItem.media_type == media_type, WatchlistItem.tmdb_id == tmdb_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted > 0


def forget_user(db: Session, user_id: int) -> None:
    """Rows go with their user (caller commits). SQLite does not enforce the foreign key, which
    is why playback and device rows are deleted by hand too."""
    db.query(WatchlistItem).filter(WatchlistItem.user_id == user_id).delete(synchronize_session=False)
