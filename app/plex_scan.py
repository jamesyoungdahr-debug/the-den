"""Plex library scan (M11e): what the owner's Plex server already has, so Discover and
Requests can say "you have this" even for titles The Den never downloaded.

Walks the chosen library sections of the configured server, reads each item's external
ids from its Guid tags (`tmdb://`, `tvdb://`, `imdb://`; legacy `com.plexapp.agents.*`
guids too), and for shows reads the seasons with their episode counts. Rows land in
plex_media; anything not seen in a completed scan is removed. Runs on a timer (see
app.scheduler) and on demand from Settings.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app import plex
from app import settings as settings_module
from app.models import PlexMedia

log = logging.getLogger(__name__)

PAGE = 100
_GUID = re.compile(r"^(tmdb|tvdb|imdb)://([A-Za-z0-9]+)")
_LEGACY = {
    "com.plexapp.agents.themoviedb": "tmdb",
    "com.plexapp.agents.thetvdb": "tvdb",
    "com.plexapp.agents.imdb": "imdb",
}
_lock = asyncio.Lock()


class NotConfigured(Exception):
    pass


def external_ids(item: dict) -> dict:
    """{'tmdb': int, 'tvdb': int, 'imdb': 'tt..'} from an item's Guid tags / legacy guid."""
    ids: dict = {}
    for g in item.get("Guid") or []:
        m = _GUID.match(str(g.get("id", "")))
        if m:
            ids.setdefault(m.group(1), m.group(2))
    legacy = str(item.get("guid") or "")
    for prefix, kind in _LEGACY.items():
        if legacy.startswith(prefix + "://"):
            value = legacy[len(prefix) + 3:].split("?")[0].split("/")[0]
            ids.setdefault(kind, value)
    out: dict = {}
    for kind in ("tmdb", "tvdb"):
        if kind in ids and str(ids[kind]).isdigit():
            out[kind] = int(ids[kind])
    if "imdb" in ids:
        out["imdb"] = str(ids["imdb"])
    return out


async def _fetch_all(client: httpx.AsyncClient, url: str, token: str, section_key: str) -> list[dict]:
    items: list[dict] = []
    start = 0
    while True:
        headers = {**plex._headers(token), "X-Plex-Container-Start": str(start), "X-Plex-Container-Size": str(PAGE)}
        resp = await client.get(f"{url}/library/sections/{section_key}/all", params={"includeGuids": "1"}, headers=headers)
        resp.raise_for_status()
        container = resp.json().get("MediaContainer", {})
        batch = container.get("Metadata") or []
        items.extend(batch)
        total = int(container.get("totalSize") or container.get("size") or len(items))
        start += len(batch)
        if not batch or start >= total:
            break
    return items


async def _seasons(client: httpx.AsyncClient, url: str, token: str, rating_key: str) -> dict[int, int]:
    resp = await client.get(f"{url}/library/metadata/{rating_key}/children", headers=plex._headers(token))
    resp.raise_for_status()
    seasons: dict[int, int] = {}
    for s in resp.json().get("MediaContainer", {}).get("Metadata") or []:
        if s.get("type") != "season" or s.get("index") is None:
            continue
        seasons[int(s["index"])] = int(s.get("leafCount") or 0)
    return seasons


async def scan(db: Session) -> dict:
    """Run a full scan. Returns a summary dict; raises NotConfigured when Plex isn't set up."""
    s = settings_module.effective(db)
    if not (s.plex_url and s.plex_token):
        raise NotConfigured()
    if _lock.locked():
        return {"skipped": True, "reason": "a scan is already running"}
    async with _lock:
        started = time.monotonic()
        movies = shows = 0
        seen: set[str] = set()
        async with httpx.AsyncClient(timeout=60, verify=False) as client:
            section_keys = list(s.plex_sections)
            if not section_keys:
                sections = await plex.library_sections(s.plex_url, s.plex_token)
                section_keys = [sec["key"] for sec in sections if sec.get("type") in ("movie", "show")]
            for key in section_keys:
                for item in await _fetch_all(client, s.plex_url, s.plex_token, key):
                    kind = item.get("type")
                    if kind not in ("movie", "show"):
                        continue
                    rating_key = str(item.get("ratingKey"))
                    ids = external_ids(item)
                    seasons = await _seasons(client, s.plex_url, s.plex_token, rating_key) if kind == "show" else None
                    row = db.query(PlexMedia).filter(PlexMedia.rating_key == rating_key).first()
                    if row is None:
                        row = PlexMedia(rating_key=rating_key, media_type="movie" if kind == "movie" else "tv", title=item.get("title") or "?")
                        db.add(row)
                    row.media_type = "movie" if kind == "movie" else "tv"
                    row.title = item.get("title") or row.title
                    row.year = item.get("year")
                    row.tmdb_id = ids.get("tmdb")
                    row.tvdb_id = ids.get("tvdb")
                    row.imdb_id = ids.get("imdb")
                    row.seasons = json.dumps(seasons) if seasons is not None else None
                    row.thumb = item.get("thumb") or None
                    row.scanned_at = datetime.now(timezone.utc)
                    seen.add(rating_key)
                    if kind == "movie":
                        movies += 1
                    else:
                        shows += 1
        removed = 0
        for row in db.query(PlexMedia).all():
            if row.rating_key not in seen:
                db.delete(row)
                removed += 1
        elapsed = time.monotonic() - started
        summary = f"{movies} movies, {shows} shows" + (f", {removed} removed" if removed else "") + f" in {elapsed:.1f}s"
        settings_row = settings_module.get_row(db)
        settings_row.plex_last_scan_at = datetime.now(timezone.utc)
        settings_row.plex_last_scan_result = summary
        db.commit()
        log.info("plex scan: %s", summary)
        return {"movies": movies, "shows": shows, "removed": removed, "seconds": round(elapsed, 1), "summary": summary}


def plex_index(db: Session) -> tuple[dict[int, PlexMedia], dict[int, PlexMedia], dict[int, PlexMedia]]:
    """tmdb_id -> movie row, tmdb_id -> show row, tvdb_id -> show row."""
    movies: dict[int, PlexMedia] = {}
    tv_by_tmdb: dict[int, PlexMedia] = {}
    tv_by_tvdb: dict[int, PlexMedia] = {}
    for row in db.query(PlexMedia):
        if row.media_type == "movie":
            if row.tmdb_id:
                movies[row.tmdb_id] = row
        else:
            if row.tmdb_id:
                tv_by_tmdb[row.tmdb_id] = row
            if row.tvdb_id:
                tv_by_tvdb[row.tvdb_id] = row
    return movies, tv_by_tmdb, tv_by_tvdb


def season_counts(row: PlexMedia | None) -> dict[int, int]:
    if row is None or not row.seasons:
        return {}
    return {int(k): int(v) for k, v in json.loads(row.seasons).items()}
