"""Blocklist (M19): releases automation must never grab again, by info hash or exact
title. Entries expire so a torrent that was merely dead for a while can be retried."""

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import BlocklistEntry, DownloadRecord

DEFAULT_DAYS = 30
_BTIH = re.compile(r"urn:btih:([0-9a-fA-F]{40}|[A-Za-z2-7]{32})", re.IGNORECASE)


def info_hash_of(url: str) -> str | None:
    """The info hash in a magnet link (lower-cased hex or base32), else None."""
    m = _BTIH.search(url or "")
    return m.group(1).lower() if m else None


def add(db: Session, record: DownloadRecord, reason: str, days: int | None = DEFAULT_DAYS) -> BlocklistEntry:
    """Blocklist the release behind a download record. days=None never expires. Commits."""
    now = datetime.now(timezone.utc)
    entry = BlocklistEntry(
        info_hash=(record.info_hash or info_hash_of(record.download_url) or None),
        release_title=record.release_title,
        reason=reason,
        movie_id=record.movie_id,
        episode_id=record.episode_id,
        created_at=now,
        expires_at=now + timedelta(days=days) if days else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def purge_expired(db: Session) -> int:
    """Delete entries past expires_at. Returns how many. Commits."""
    now = datetime.now(timezone.utc)
    count = db.query(BlocklistEntry).filter(BlocklistEntry.expires_at.isnot(None), BlocklistEntry.expires_at < now).delete(synchronize_session=False)
    db.commit()
    return count


def active(db: Session) -> list[BlocklistEntry]:
    """Entries that are still in force, newest first."""
    now = datetime.now(timezone.utc)
    return (
        db.query(BlocklistEntry)
        .filter((BlocklistEntry.expires_at.is_(None)) | (BlocklistEntry.expires_at >= now))
        .order_by(BlocklistEntry.id.desc())
        .all()
    )


def blocked_keys(db: Session) -> tuple[set[str], set[str]]:
    """(info hashes, lower-cased titles) of every active entry, for cheap filtering."""
    hashes: set[str] = set()
    titles: set[str] = set()
    for entry in active(db):
        if entry.info_hash:
            hashes.add(entry.info_hash.lower())
        titles.add(entry.release_title.strip().lower())
    return hashes, titles


def is_blocked(title: str, url: str, keys: tuple[set[str], set[str]]) -> bool:
    hashes, titles = keys
    h = info_hash_of(url)
    return (h is not None and h in hashes) or (title or "").strip().lower() in titles
