"""Discover (M11d): browse TMDB -- trending, popular, upcoming, recommendations, search,
and movie/series detail pages -- with the library's and Plex's status merged onto every
card (M11e), request state (M11f), and admin actions to add a title straight into the
library. JSON twins for the companion apps."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import health
from app import auth, plex_scan, requests_service, tmdb, tvmaze
from app import history
from app import settings as settings_module
from app.deps import get_db
from app.models import DownloadRecord, Episode, MediaRequest, Movie, Series, User
from app.templating import templates

log = logging.getLogger(__name__)
router = APIRouter(tags=["discover"])
USER = [Depends(auth.page_user)]
ADMIN = [Depends(auth.page_admin)]


# ---- status on TMDB cards --------------------------------------------------------------

class Index:
    """Everything needed to stamp a status on a TMDB card, loaded once per page."""

    def __init__(self, db: Session):
        self.movies: dict[int, Movie] = {m.tmdb_id: m for m in db.query(Movie)}
        self.series: dict[int, dict] = {}
        rows = db.query(Series).filter(Series.tmdb_id.isnot(None)).all()
        if rows:
            ids = [s.id for s in rows]
            totals: dict[int, int] = {}
            haves: dict[int, int] = {}
            for sid, has_file in db.query(Episode.series_id, Episode.has_file).filter(Episode.series_id.in_(ids)):
                totals[sid] = totals.get(sid, 0) + 1
                haves[sid] = haves.get(sid, 0) + (1 if has_file else 0)
            for s in rows:
                self.series[s.tmdb_id] = {"series": s, "have": haves.get(s.id, 0), "total": totals.get(s.id, 0)}
        self.plex_movies, self.plex_tv, self.plex_tv_tvdb = plex_scan.plex_index(db)
        self.requested: dict[tuple[str, int], str] = {
            (r.media_type, r.tmdb_id): r.status
            for r in db.query(MediaRequest).filter(MediaRequest.status.in_(requests_service.OPEN_STATUSES))
        }

    def stamp(self, item: dict) -> dict:
        """status: available | partial | wanted | requested | None, plus on_plex / library_href."""
        kind, tid = item["media_type"], item["tmdb_id"]
        status = None
        if kind == "movie":
            m, p = self.movies.get(tid), self.plex_movies.get(tid)
            item["on_plex"] = p is not None
            if (m is not None and m.has_file) or p is not None:
                status = "available"
            elif m is not None:
                status = "wanted"
            if m is not None:
                item["library_href"] = "/library"
        else:
            s, p = self.series.get(tid), self.plex_tv.get(tid)
            item["on_plex"] = p is not None
            complete = s is not None and s["total"] and s["have"] == s["total"]
            if complete or (p is not None and s is None):
                status = "available"
            elif (s is not None and s["have"]) or p is not None:
                status = "partial"
            elif s is not None:
                status = "wanted"
            if s is not None:
                item["library_href"] = f"/ui/series/{s['series'].id}"
        req = self.requested.get((kind, tid))
        if status is None and req == "pending":
            status = "requested"
        elif status is None and req == "approved":
            status = "wanted"
        item["status"] = status
        return item


def _decorate(items: list[dict], db: Session) -> list[dict]:
    idx = Index(db)
    return [idx.stamp(i) for i in items]


async def _rails(api_key: str) -> tuple[dict[str, list[dict]], list[str]]:
    """Fetch every home rail at once; a failing rail is reported, not fatal."""
    names = list(RAILS)
    results = await asyncio.gather(*(RAILS[name][3](api_key) for name in names), return_exceptions=True)
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


async def _recommended_for_you(db: Session, api_key: str, idx: Index) -> list[dict]:
    """TMDB's recommendations for the titles most recently added to the library, merged,
    de-duplicated, minus anything already in the library or on Plex, best-rated first."""
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
            if rec["media_type"] == "movie" and (rec["tmdb_id"] in idx.movies or rec["tmdb_id"] in idx.plex_movies):
                continue
            if rec["media_type"] == "tv" and (rec["tmdb_id"] in idx.series or rec["tmdb_id"] in idx.plex_tv):
                continue
            seen.add(key)
            picks.append(idx.stamp(rec))
    picks.sort(key=lambda r: (r.get("rating") or 0), reverse=True)
    return picks[:18]


# ---- HTML -----------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse, dependencies=USER)
async def discover_home(request: Request, db: Session = Depends(get_db)):
    api_key = settings_module.effective(db).tmdb_api_key
    rails, errors = await _rails(api_key) if api_key else ({}, ["no_key"])
    idx = Index(db)
    recommended = await _recommended_for_you(db, api_key, idx) if api_key else []
    for name in rails:
        rails[name] = [idx.stamp(i) for i in rails[name]]
    hero = next((i for i in rails.get("trending", []) if i.get("backdrop_path")), None)
    movie_rails = [(key, spec[0], spec[1], rails.get(key, [])) for key, spec in RAILS.items() if spec[2] == "movie"]
    tv_rails = [(key, spec[0], spec[1], rails.get(key, [])) for key, spec in RAILS.items() if spec[2] == "tv"]
    stats = {
        "movies": len(idx.movies),
        "series": db.query(Series).count(),
        "downloading": db.query(DownloadRecord).filter(DownloadRecord.status.notin_(["imported", "failed"])).count(),
        "plex": len(idx.plex_movies) + len(idx.plex_tv),
    }
    return templates.TemplateResponse(
        "discover.html",
        {
            "request": request, "rails": rails, "errors": errors, "hero": hero, "recommended": recommended,
            "stats": stats, "has_key": bool(api_key), "active_nav": "discover", "movie_rails": movie_rails, "tv_rails": tv_rails,
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


@router.get("/discover/rail/{rail}", response_class=HTMLResponse, dependencies=USER)
async def discover_rail(request: Request, rail: str, page: int = 1, db: Session = Depends(get_db)):
    """One rail as a full paged grid ("View more" from the home page)."""
    spec = RAILS.get(rail)
    if spec is None:
        raise HTTPException(404, "Unknown rail")
    title, subtitle, kind, call = spec
    api_key = settings_module.effective(db).tmdb_api_key
    page = max(1, min(page, 500))
    results: list[dict] = []
    error = None
    if not api_key:
        error = "Discover needs a TMDB key (Settings > Library)."
    else:
        try:
            results = _decorate(await call(api_key, page=page), db)
        except Exception as exc:
            error = f"TMDB didn't answer: {exc}"
    return templates.TemplateResponse(
        "discover_rail.html",
        {"request": request, "rail_key": rail, "title": title, "subtitle": subtitle, "kind": kind, "page": page,
         "results": results, "has_more": len(results) >= 20, "error": error, "active_nav": "discover"},
    )


async def _detail(kind: str, tmdb_id: int, db: Session, me: User | None = None) -> dict | None:
    api_key = settings_module.effective(db).tmdb_api_key
    item = await (tmdb.movie_details if kind == "movie" else tmdb.tv_details)(tmdb_id, api_key)
    if item is None:
        return None
    idx = Index(db)
    idx.stamp(item)
    item["recommendations"] = [idx.stamp(r) for r in item.get("recommendations", [])]
    av = requests_service.availability(db, kind, tmdb_id, item.get("tvdb_id"))
    item["availability"] = {
        "den": av["den"], "plex": av["plex"], "available": av["available"] if kind == "movie" else None,
        "available_seasons": sorted(av["available_seasons"]),
    }
    item["library"] = av["den"]
    open_reqs = requests_service.open_requests_for(db, kind, tmdb_id)
    names = {u.id: u.username for u in db.query(User).filter(User.id.in_({r.requested_by for r in open_reqs}))} if open_reqs else {}
    item["requests"] = [
        {"id": r.id, "status": r.status, "seasons": r.season_list, "by": names.get(r.requested_by, "?"), "mine": bool(me and r.requested_by == me.id)}
        for r in open_reqs
    ]
    if kind == "tv":
        taken = set(av["available_seasons"])
        den = av["den"] or {}
        for n, r in (den.get("seasons") or {}).items():
            if r["monitored"] and r["have"] < r["total"]:
                taken.add(n)
        for r in open_reqs:
            taken |= set(r.season_list) if r.season_list else {s["season_number"] for s in item["seasons"]}
        item["requestable_seasons"] = [s["season_number"] for s in item["seasons"] if s["season_number"] > 0 and s["season_number"] not in taken]
    item["history"] = history.as_dicts(history.for_movie(db, av["den"]["id"]) if kind == "movie" and av["den"] else history.for_series(db, av["den"]["id"]) if kind == "tv" and av["den"] else [])
    return item


@router.get("/discover/movie/{tmdb_id}", response_class=HTMLResponse, dependencies=USER)
async def discover_movie(request: Request, tmdb_id: int, db: Session = Depends(get_db)):
    item = await _detail("movie", tmdb_id, db, getattr(request.state, "user", None))
    if item is None:
        raise HTTPException(404, "Movie not found on TMDB")
    return templates.TemplateResponse(
        "discover_detail.html",
        {"request": request, "item": item, "kind": "movie", "notice": request.query_params.get("notice"),
         "error": request.query_params.get("error"), "active_nav": "discover"},
    )


@router.get("/discover/tv/{tmdb_id}", response_class=HTMLResponse, dependencies=USER)
async def discover_tv(request: Request, tmdb_id: int, db: Session = Depends(get_db)):
    item = await _detail("tv", tmdb_id, db, getattr(request.state, "user", None))
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

# rail key -> (title, subtitle, kind, tmdb call). kind ("all" | "movie" | "tv") groups the home page.
RAILS = {
    "trending": ("Trending this week", "movies and series", "all", tmdb.trending),
    "trending-movies": ("Trending movies", "this week on TMDB", "movie", tmdb.trending_movies),
    "popular-movies": ("Popular movies", "", "movie", tmdb.popular_movies),
    "upcoming-movies": ("Upcoming movies", "in cinemas soon", "movie", tmdb.upcoming_movies),
    "top-rated-movies": ("Top rated movies", "all time, by TMDB votes", "movie", tmdb.top_rated_movies),
    "trending-tv": ("Trending series", "this week on TMDB", "tv", tmdb.trending_tv),
    "popular-tv": ("Popular series", "", "tv", tmdb.popular_tv),
    "on-the-air": ("On the air", "series with new episodes this week", "tv", tmdb.on_the_air),
    "top-rated-tv": ("Top rated series", "all time, by TMDB votes", "tv", tmdb.top_rated_tv),
}
_RAIL_CALLS = {key: spec[3] for key, spec in RAILS.items()}


@router.get("/api/discover/recommended", dependencies=[Depends(auth.require_user)])
async def api_recommended(db: Session = Depends(get_db)):
    api_key = settings_module.effective(db).tmdb_api_key
    return await _recommended_for_you(db, api_key, Index(db))


@router.get("/api/discover/search", dependencies=[Depends(auth.require_user)])
async def api_search(q: str, db: Session = Depends(get_db)):
    api_key = settings_module.effective(db).tmdb_api_key
    return _decorate(await tmdb.search_multi(q, api_key), db)


@router.get("/api/discover/movie/{tmdb_id}", dependencies=[Depends(auth.require_user)])
async def api_movie(request: Request, tmdb_id: int, db: Session = Depends(get_db)):
    item = await _detail("movie", tmdb_id, db, getattr(request.state, "user", None))
    if item is None:
        raise HTTPException(404, "Movie not found on TMDB")
    return item


@router.get("/api/discover/tv/{tmdb_id}", dependencies=[Depends(auth.require_user)])
async def api_tv(request: Request, tmdb_id: int, db: Session = Depends(get_db)):
    item = await _detail("tv", tmdb_id, db, getattr(request.state, "user", None))
    if item is None:
        raise HTTPException(404, "Series not found on TMDB")
    return item


@router.get("/api/discover/{rail}", dependencies=[Depends(auth.require_user)])
async def api_rail(rail: str, page: int = 1, db: Session = Depends(get_db)):
    call = _RAIL_CALLS.get(rail)
    if call is None:
        raise HTTPException(404, f"Unknown rail; one of {', '.join(_RAIL_CALLS)}, recommended")
    api_key = settings_module.effective(db).tmdb_api_key
    return _decorate(await call(api_key, page=max(1, min(page, 500))), db)
