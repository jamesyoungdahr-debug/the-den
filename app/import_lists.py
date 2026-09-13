"""E1: import lists -- auto-add movies/series from a TMDB list or a Plex watchlist on a
schedule, the same way approving a request does (get_or_create_movie/series), just
without a MediaRequest in between."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import plex, requests_service, tmdb
from app import settings as settings_module
from app.models import ImportList, Movie, Series

log = logging.getLogger(__name__)


async def sync_one(db: Session, il: ImportList) -> str:
    """Fetch this list's items and add any not already in the library. Sets
    last_synced_at/last_result and commits. Returns the result string."""
    s = settings_module.effective(db)
    config = json.loads(il.config or "{}")
    try:
        if il.kind == "tmdb_list":
            list_id = config.get("list_id")
            if not list_id:
                raise ValueError("no list_id configured")
            items = await tmdb.get_list(str(list_id), s.tmdb_api_key)
        elif il.kind == "plex_watchlist":
            if not s.plex_token:
                raise ValueError("Plex isn't connected")
            items = await plex.watchlist(s.plex_token)
        else:
            raise ValueError(f"unknown kind {il.kind!r}")
    except Exception as exc:
        il.last_result = f"failed: {exc}"
        il.last_synced_at = datetime.now(timezone.utc)
        db.commit()
        return il.last_result

    added = skipped = failed = 0
    for item in items:
        tmdb_id, media_type = item.get("tmdb_id"), item.get("media_type")
        if not tmdb_id or media_type not in ("movie", "tv"):
            continue
        try:
            if media_type == "movie":
                existing = db.query(Movie).filter(Movie.tmdb_id == tmdb_id).first()
                if existing:
                    skipped += 1
                    continue
                movie, _ = await requests_service.get_or_create_movie(db, tmdb_id, item.get("title"))
                if il.quality_profile_id:
                    movie.quality_profile_id = il.quality_profile_id
                added += 1
            else:
                existing = db.query(Series).filter(Series.tmdb_id == tmdb_id).first()
                if existing:
                    skipped += 1
                    continue
                series, _ = await requests_service.get_or_create_series(db, tmdb_id)
                if series and il.quality_profile_id:
                    series.quality_profile_id = il.quality_profile_id
                added += 1
        except Exception:
            log.warning("import list %s: failed to add tmdb_id=%s", il.name, tmdb_id, exc_info=True)
            failed += 1
    db.commit()
    parts = [f"{added} added"]
    if skipped:
        parts.append(f"{skipped} already in the library")
    if failed:
        parts.append(f"{failed} failed")
    il.last_result = ", ".join(parts) if (added or skipped or failed) else "0 items"
    il.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    return il.last_result


async def sync_all(db: Session) -> list[dict]:
    """Sync every enabled import list. Called by the scheduler and by a manual "sync all"."""
    results = []
    for il in db.query(ImportList).filter(ImportList.enabled == True).all():  # noqa: E712
        result = await sync_one(db, il)
        results.append({"id": il.id, "name": il.name, "result": result})
    return results
