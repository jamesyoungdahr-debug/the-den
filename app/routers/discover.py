"""Discover (M11d): browse TMDB -- trending, popular, upcoming, recommendations, search,
and movie/series detail pages -- with the library's status merged onto every card, and
admin actions to add a title straight into the library. JSON twins for the companion apps."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import auth, tmdb, tvmaze
from app import settings as settings_module
from app.deps import get_db
from app.models import DownloadRecord, Episode, Movie, Series
from app.templating import templates

log = logging.getLogger(__name__)
router = APIRouter(tags=["discover"])
USER = [Depends(auth.page_user)]
ADMIN = [Depends(auth.page_admin)]


# ---- library status on TMDB cards ---------------------------------------------------

def _library_index(db: Session) -> tuple[dict[int, Movie], dict[int, dict]]:
    """tmdb_id -> Movie, and tmdb_id -> {series, have, total} for series that carry a tmdb_id."""
    movies = {m.tmdb_id: m for m in db.query(Movie)}
    series_rows = db.query(Series).filter(Series.tmdb_id.isnot(None)).all()
    series: dict[int, dict] = {}
    if series_rows:
        ids = [s.id for s in series_rows]
        totals: dict[int, int] = {}
        haves: dict[int, int] = {}
        for sid, has_file in db.query(Episode.series_id, Episode.has_file).filter(Episode.series_id.in_(ids)):
            totals[sid] = totals.get(sid, 0) + 1
            haves[sid] = haves.get(sid, 0) + (1 if has_file else 0)
        for s in series_rows:
            series[s.tmdb_id] = {"series": s, "have": haves.get(s.id, 0), "total": totals.get(s.id, 0)}
    return movies, series


def _status(item: dict, movies: dict[int, Movie], series: dict[int, dict]) -> dict:
    """Adds status (available | partial | wanted | None) and a library link to a card."""
    if item["media_type"] == "movie":
        m = movies.get(item["tmdb_id"])
        if m is not None:
            item["status"] = "available" if m.has_file else "wanted"
            item["library_href"] = "/library"
    else:
        s = series.get(item["tmdb_id"])
        if s is not None:
            if s["total"] and s["have"] == s["total"]:
                item["status"] = "available"
            elif s["have"]:
                item["status"] = "partial"
            else:
                item["status"] = "wanted"
            item["library_href"] = f"/ui/series/{s['series'].id}"
    item.setdefault("status", None)
    return item


def _decorate(items: list[dict], db: Session) -> list[dict]:
    movies, series = _library_index(db)
    return [_status(i, movies, series) for i in items]


async def _rails(api_key: str) -> tuple[dict[str, list[dict]], list[str]]:
    """Fetch every home rail at once; a failing rail is reported, not fatal."""
    names = ["trending", "popular_movies", "upcoming_movies", "popular_tv", "on_the_air"]
    calls = [tmdb.trending(api_key), tmdb.popular_movies(api_key), tmdb.upcoming_movies(api_key), tmdb.popular_tv(api_key), tmdb.on_the_air(api_key)]
    results = await asyncio.gather(*calls, return_exceptions=True)
    rails: dict[str, list[dict]] = {}
    errors: list[str] = []
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            log.warning("discover rail %s failed: %s", name, result)
            errors.append(name)
            rails[name] = []
        else:
            rails[name] = result
    return rails, errors


async def _recommended_for_you(db: Session, api_key: str, movies: dict[int, Movie], series: dict[int, dict]) -> list[dict]:
    """TMDB's recommendations for the titles most recently added to the library, merged,
    de-duplicated, minus anything already in the library, best-rated first."""
    recent_movies = db.query(Movie).order_by(Movie.id.desc()).limit(6).all()
    recent_series = db.query(Series).filter(Series.tmdb_id.isnot(None)).order_by(Series.id.desc()).limit(4).all()
    calls = [tmdb.movie_details(m.tmdb_id, api_key) for m in recent_movies] + [tmdb.tv_details(s.tmdb_id, api_key) for s in recent_series]
    if not calls:
        return []
    details = await asyncio.gather(*calls, return_exceptions=True)
    seen: set[tuple[str, int]] = set()
    picks: list[dict] = []
    for d in details:
        if isinstance(d, Exception) or not d:
            continue
        for rec in d.get("recommendations", []):
            key = (rec["media_type"], rec["tmdb_id"])
            if key in seen:
                continue
            if rec["media_type"] == "movie" and rec["tmdb_id"] in movies:
                continue
            if rec["media_type"] == "tv" and rec["tmdb_id"] in series:
                continue
            seen.add(key)
            picks.append(rec)
    picks.sort(key=lambda r: (r.get("rating") or 0), reverse=True)
    return picks[:18]


# ---- HTML -----------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse, dependencies=USER)
async def discover_home(request: Request, db: Session = Depends(get_db)):
    api_key = settings_module.effective(db).tmdb_api_key
    rails, errors = await _rails(api_key) if api_key else ({}, ["no_key"])
    movies, series = _library_index(db)
    recommended = await _recommended_for_you(db, api_key, movies, series) if api_key else []
    for name in rails:
        rails[name] = [_status(i, movies, series) for i in rails[name]]
    hero = next((i for i in rails.get("trending", []) if i.get("backdrop_path")), None)
    stats = {
        "movies": len(movies),
        "series": db.query(Series).count(),
        "downloading": db.query(DownloadRecord).filter(DownloadRecord.status.notin_(["imported", "failed"])).count(),
    }
    return templates.TemplateResponse(
        "discover.html",
        {
            "request": request, "rails": rails, "errors": errors, "hero": hero, "recommended": recommended,
            "stats": stats, "has_key": bool(api_key), "active_nav": "discover",
        },
    )


@router.get("/discover/search", response_class=HTMLResponse, dependencies=USER)
async def discover_search(request: Request, q: str = "", type: str = "all", db: Session = Depends(get_db)):
    api_key = settings_module.effective(db).tmdb_api_key
    results: list[dict] = []
    error = None
    if q.strip():
        try:
            results = _decorate(await tmdb.search_multi(q.strip(), api_key), db)
        except Exception as exc:
            error = f"TMDB search failed: {exc}"
    if type in ("movie", "tv"):
        results = [r for r in results if r["media_type"] == type]
    return templates.TemplateResponse(
        "discover_search.html",
        {"request": request, "query": q, "type": type, "results": results, "error": error, "active_nav": "discover"},
    )


async def _detail(kind: str, tmdb_id: int, db: Session) -> dict | None:
    api_key = settings_module.effective(db).tmdb_api_key
    item = await (tmdb.movie_details if kind == "movie" else tmdb.tv_details)(tmdb_id, api_key)
    if item is None:
        return None
    movies, series = _library_index(db)
    _status(item, movies, series)
    item["recommendations"] = [_status(r, movies, series) for r in item.get("recommendations", [])]
    if kind == "movie":
        m = movies.get(tmdb_id)
        item["library"] = {"id": m.id, "has_file": m.has_file} if m else None
    else:
        s = series.get(tmdb_id)
        item["library"] = None
        if s:
            per_season: dict[int, dict] = {}
            for e in db.query(Episode).filter(Episode.series_id == s["series"].id):
                row = per_season.setdefault(e.season_number, {"have": 0, "total": 0})
                row["total"] += 1
                row["have"] += 1 if e.has_file else 0
            item["library"] = {"id": s["series"].id, "have": s["have"], "total": s["total"], "seasons": per_season}
    return item


@router.get("/discover/movie/{tmdb_id}", response_class=HTMLResponse, dependencies=USER)
async def discover_movie(request: Request, tmdb_id: int, db: Session = Depends(get_db)):
    item = await _detail("movie", tmdb_id, db)
    if item is None:
        raise HTTPException(404, "Movie not found on TMDB")
    return templates.TemplateResponse(
        "discover_detail.html",
        {"request": request, "item": item, "kind": "movie", "notice": request.query_params.get("notice"),
         "error": request.query_params.get("error"), "active_nav": "discover"},
    )


@router.get("/discover/tv/{tmdb_id}", response_class=HTMLResponse, dependencies=USER)
async def discover_tv(request: Request, tmdb_id: int, db: Session = Depends(get_db)):
    item = await _detail("tv", tmdb_id, db)
    if item is None:
        raise HTTPException(404, "Series not found on TMDB")
    return templates.TemplateResponse(
        "discover_detail.html",
        {"request": request, "item": item, "kind": "tv", "notice": request.query_params.get("notice"),
         "error": request.query_params.get("error"), "active_nav": "discover"},
    )


# ---- add to library (admin) --------------------------------------------------------------

@router.post("/ui/discover/movie/{tmdb_id}/add", dependencies=ADMIN)
async def add_movie_from_discover(tmdb_id: int, db: Session = Depends(get_db)):
    if db.query(Movie).filter(Movie.tmdb_id == tmdb_id).first() is None:
        api_key = settings_module.effective(db).tmdb_api_key
        item = await tmdb.movie_details(tmdb_id, api_key)
        if item is None:
            raise HTTPException(404, "Movie not found on TMDB")
        db.add(Movie(tmdb_id=tmdb_id, title=item["title"], year=item["year"], overview=item["overview"], poster_path=item["poster_path"]))
        db.commit()
    return RedirectResponse(f"/discover/movie/{tmdb_id}?notice=Added+to+the+library.+Automation+will+look+for+it.", status_code=303)


async def map_tv_to_tvmaze(item: dict) -> dict | None:
    """TMDB series -> TVmaze show: by TVDB id, then IMDb id, then an exact-title search."""
    show = None
    if item.get("tvdb_id"):
        show = await tvmaze.lookup_show(thetvdb=item["tvdb_id"])
    if show is None and item.get("imdb_id"):
        show = await tvmaze.lookup_show(imdb=item["imdb_id"])
    if show is None:
        show = await tvmaze.find_show(item["title"], item.get("year"))
    return show


@router.post("/ui/discover/tv/{tmdb_id}/add", dependencies=ADMIN)
async def add_tv_from_discover(tmdb_id: int, db: Session = Depends(get_db)):
    existing = db.query(Series).filter(Series.tmdb_id == tmdb_id).first()
    if existing is not None:
        return RedirectResponse(f"/ui/series/{existing.id}", status_code=303)
    api_key = settings_module.effective(db).tmdb_api_key
    item = await tmdb.tv_details(tmdb_id, api_key)
    if item is None:
        raise HTTPException(404, "Series not found on TMDB")
    try:
        show = await map_tv_to_tvmaze(item)
    except Exception as exc:
        return RedirectResponse(f"/discover/tv/{tmdb_id}?error=TVmaze+lookup+failed:+{exc}", status_code=303)
    if show is None:
        return RedirectResponse(f"/discover/tv/{tmdb_id}?error=Couldn%27t+match+this+series+on+TVmaze,+which+The+Den+uses+for+episode+lists.+Add+it+from+the+TV+page+by+name+instead.", status_code=303)
    already = db.query(Series).filter(Series.tvmaze_id == show["tvmaze_id"]).first()
    if already is not None:
        already.tmdb_id = tmdb_id  # same show added earlier by name; now it's linked
        db.commit()
        return RedirectResponse(f"/ui/series/{already.id}", status_code=303)
    episodes = await tvmaze.get_tv_episodes(show["tvmaze_id"])
    series = Series(
        tvmaze_id=show["tvmaze_id"], tmdb_id=tmdb_id, title=item["title"], year=item["year"] or show["year"],
        overview=item["overview"] or show["overview"], poster_path=item["poster_path"] or show["poster_path"],
    )
    db.add(series)
    db.commit()
    db.refresh(series)
    for ep in episodes:
        db.add(Episode(series_id=series.id, **ep))
    db.commit()
    return RedirectResponse(f"/ui/series/{series.id}", status_code=303)


# ---- JSON -----------------------------------------------------------------------------

_RAIL_CALLS = {
    "trending": tmdb.trending, "popular-movies": tmdb.popular_movies, "upcoming-movies": tmdb.upcoming_movies,
    "popular-tv": tmdb.popular_tv, "on-the-air": tmdb.on_the_air,
}


@router.get("/api/discover/recommended", dependencies=[Depends(auth.require_user)])
async def api_recommended(db: Session = Depends(get_db)):
    api_key = settings_module.effective(db).tmdb_api_key
    movies, series = _library_index(db)
    return await _recommended_for_you(db, api_key, movies, series)


@router.get("/api/discover/search", dependencies=[Depends(auth.require_user)])
async def api_search(q: str, db: Session = Depends(get_db)):
    api_key = settings_module.effective(db).tmdb_api_key
    return _decorate(await tmdb.search_multi(q, api_key), db)


@router.get("/api/discover/movie/{tmdb_id}", dependencies=[Depends(auth.require_user)])
async def api_movie(tmdb_id: int, db: Session = Depends(get_db)):
    item = await _detail("movie", tmdb_id, db)
    if item is None:
        raise HTTPException(404, "Movie not found on TMDB")
    return item


@router.get("/api/discover/tv/{tmdb_id}", dependencies=[Depends(auth.require_user)])
async def api_tv(tmdb_id: int, db: Session = Depends(get_db)):
    item = await _detail("tv", tmdb_id, db)
    if item is None:
        raise HTTPException(404, "Series not found on TMDB")
    return item


@router.get("/api/discover/{rail}", dependencies=[Depends(auth.require_user)])
async def api_rail(rail: str, db: Session = Depends(get_db)):
    call = _RAIL_CALLS.get(rail)
    if call is None:
        raise HTTPException(404, f"Unknown rail; one of {', '.join(_RAIL_CALLS)}, recommended")
    api_key = settings_module.effective(db).tmdb_api_key
    return _decorate(await call(api_key), db)
