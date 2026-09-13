"""The library as people actually see it: what The Den manages *and* what the Plex scan
found, merged into one list per media type. A title can be in The Den (wanted or on
disk), only on Plex (never downloaded by The Den), or both.

Each entry is a plain dict so the HTML pages and the JSON API share it:
  source        "den" | "plex" | "both"
  id            The Den's row id, or None for Plex-only entries
  tmdb_id       TMDB id when known (Den rows always; Plex rows when the agent gave one)
  title, year, poster_path (a TMDB path, a TVmaze URL, or /api/plex/thumb/{rating_key})
  has_file      movies: The Den has the file (Plex-only entries count as available)
  have, total   series: episode counts in The Den (0/0 for Plex-only)
  on_plex       True when the Plex scan saw it
  plex_seasons  series: {season_number: episode_count} from Plex
  available     movies: has_file or on_plex; series: complete in The Den or on Plex
"""

from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.models import DownloadRecord, Episode, Movie, PlexMedia, QualityProfile, Series
from app.candidates import profile_for
from app.scoring import is_upgradable


def _norm(title: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def plex_thumb_url(row: PlexMedia) -> str:
    return f"/api/plex/thumb/{row.rating_key}" if row.thumb else ""


def _downloading_movie_ids(db: Session) -> set[int]:
    rows = db.query(DownloadRecord.movie_id).filter(
        DownloadRecord.movie_id.isnot(None), DownloadRecord.status.notin_(["imported", "failed"])
    )
    return {r[0] for r in rows}


def merged_movies(db: Session) -> list[dict]:
    plex_rows = db.query(PlexMedia).filter(PlexMedia.media_type == "movie").all()
    plex_by_tmdb = {p.tmdb_id: p for p in plex_rows if p.tmdb_id}
    plex_by_title = {(_norm(p.title), p.year): p for p in plex_rows}
    downloading = _downloading_movie_ids(db)
    default_profile = db.query(QualityProfile).first()
    out: list[dict] = []
    matched: set[str] = set()
    for m in db.query(Movie).order_by(Movie.id.desc()).all():
        p = plex_by_tmdb.get(m.tmdb_id) or plex_by_title.get((_norm(m.title), m.year))
        if p is not None:
            matched.add(p.rating_key)
        profile = profile_for(db, m.quality_profile_id, default=default_profile)
        upgradable = bool(m.has_file and profile and is_upgradable(m.file_quality, m.file_score, profile))
        out.append({
            "source": "both" if p else "den", "id": m.id, "tmdb_id": m.tmdb_id, "title": m.title, "year": m.year,
            "poster_path": m.poster_path or (plex_thumb_url(p) if p else ""), "has_file": bool(m.has_file),
            "downloading": m.id in downloading, "on_plex": p is not None, "plex_rating_key": p.rating_key if p else None,
            "available": bool(m.has_file) or p is not None,
            "file_quality": m.file_quality or "", "file_score": m.file_score or 0, "upgradable": upgradable,
        })
    plex_only = [p for p in plex_rows if p.rating_key not in matched]
    for p in sorted(plex_only, key=lambda r: _norm(r.title)):
        out.append({
            "source": "plex", "id": None, "tmdb_id": p.tmdb_id, "title": p.title, "year": p.year,
            "poster_path": plex_thumb_url(p), "has_file": False, "downloading": False, "on_plex": True,
            "plex_rating_key": p.rating_key, "available": True,
            "file_quality": "", "file_score": 0, "upgradable": False,
        })
    return out


def merged_series(db: Session) -> list[dict]:
    plex_rows = db.query(PlexMedia).filter(PlexMedia.media_type == "tv").all()
    plex_by_tmdb = {p.tmdb_id: p for p in plex_rows if p.tmdb_id}
    plex_by_title = {(_norm(p.title), p.year): p for p in plex_rows}
    series_list = db.query(Series).order_by(Series.id.desc()).all()
    ids = [s.id for s in series_list]
    totals: dict[int, int] = {}
    haves: dict[int, int] = {}
    if ids:
        for series_id, has_file in db.query(Episode.series_id, Episode.has_file).filter(Episode.series_id.in_(ids)):
            totals[series_id] = totals.get(series_id, 0) + 1
            if has_file:
                haves[series_id] = haves.get(series_id, 0) + 1

    def seasons_of(p: PlexMedia | None) -> dict[int, int]:
        if p is None or not p.seasons:
            return {}
        try:
            return {int(k): int(v) for k, v in json.loads(p.seasons).items()}
        except (ValueError, AttributeError):
            return {}

    out: list[dict] = []
    matched: set[str] = set()
    for s in series_list:
        p = (plex_by_tmdb.get(s.tmdb_id) if s.tmdb_id else None) or plex_by_title.get((_norm(s.title), s.year))
        if p is not None:
            matched.add(p.rating_key)
        total, have = totals.get(s.id, 0), haves.get(s.id, 0)
        out.append({
            "source": "both" if p else "den", "id": s.id, "tmdb_id": s.tmdb_id, "tvmaze_id": s.tvmaze_id, "title": s.title,
            "year": s.year, "poster_path": s.poster_path or (plex_thumb_url(p) if p else ""), "have": have, "total": total,
            "on_plex": p is not None, "plex_seasons": seasons_of(p), "plex_rating_key": p.rating_key if p else None,
            "available": (total > 0 and have == total) or p is not None,
        })
    plex_only = [p for p in plex_rows if p.rating_key not in matched]
    for p in sorted(plex_only, key=lambda r: _norm(r.title)):
        out.append({
            "source": "plex", "id": None, "tmdb_id": p.tmdb_id, "tvmaze_id": None, "title": p.title, "year": p.year,
            "poster_path": plex_thumb_url(p), "have": 0, "total": 0, "on_plex": True, "plex_seasons": seasons_of(p),
            "plex_rating_key": p.rating_key, "available": True,
        })
    return out
