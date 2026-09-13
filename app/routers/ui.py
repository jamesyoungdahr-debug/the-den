import json
from calendar import monthrange
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import indexers as indexer_engine
from app import auth, config, library_service
from app import settings as settings_module
from app import tmdb, torznab, tvmaze
from app.candidates import episode_query, movie_query, profile_for, scored_candidates, season_candidates
from app import automation, blocklist
from app.scoring import is_upgradable
from app.deps import get_db
from app.download_check import check_and_import
from app.grabber import grab_episode as do_grab_episode, grab_season as do_grab_season
from app.grabber import grab_movie as do_grab_movie
from app.models import BlocklistEntry, DownloadRecord, Episode, Indexer, Movie, Series
from app.routers.api_settings import apply_runtime_changes
from app.routers.downloads import assign_download as _assign_download_action, import_as_is as _import_as_is_action, _unmatched_entry
from app.schemas import AssignBody, ImportAsIsBody
from app.templating import templates
from app.torrent import engine as torrent_engine

router = APIRouter(tags=["ui"])

# Route guards (see app/auth.py): pages anyone signed in may see vs. admin plumbing.

def _unmatched_records(db: Session) -> list[DownloadRecord]:
    """Every DownloadRecord with at least one leftover file an admin needs to place by hand."""
    return [r for r in db.query(DownloadRecord).filter(DownloadRecord.unmatched_files.isnot(None)).all() if json.loads(r.unmatched_files or "[]")]


USER = [Depends(auth.page_user)]
ADMIN = [Depends(auth.page_admin)]


def _series_rows(db: Session, series_list: list[Series]) -> list[dict]:
    """Series with have/total episode counts, in one query instead of one per series."""
    ids = [s.id for s in series_list]
    totals: dict[int, int] = {}
    haves: dict[int, int] = {}
    if ids:
        for series_id, has_file in db.query(Episode.series_id, Episode.has_file).filter(Episode.series_id.in_(ids)):
            totals[series_id] = totals.get(series_id, 0) + 1
            if has_file:
                haves[series_id] = haves.get(series_id, 0) + 1
    return [{"series": s, "total": totals.get(s.id, 0), "have": haves.get(s.id, 0)} for s in series_list]


def _downloading_movie_ids(db: Session) -> set[int]:
    rows = db.query(DownloadRecord.movie_id).filter(
        DownloadRecord.movie_id.isnot(None), DownloadRecord.status.notin_(["imported", "failed"])
    )
    return {movie_id for (movie_id,) in rows}


@router.get("/ui/indexers", response_class=HTMLResponse, dependencies=ADMIN)  # GET /indexers is the JSON API
async def indexers_page(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    indexers = db.query(Indexer).all()
    results = None
    if q:
        gathered = await indexer_engine.search_all(db, q, [i for i in indexers if i.enabled])
        gathered.sort(key=lambda r: r.seeders or 0, reverse=True)
        results = gathered
    return templates.TemplateResponse(
        "indexers.html",
        {"request": request, "indexers": indexers, "query": q, "results": results, "active_nav": "indexers",
         "presets": indexer_engine.as_dicts()},
    )


@router.post("/ui/indexers", dependencies=ADMIN)
def ui_create_indexer(
    name: str = Form(...),
    url: str = Form(...),
    api_key: str = Form(""),
    protocol: str = Form("torznab"),
    preset: str = Form(""),
    db: Session = Depends(get_db),
):
    chosen = indexer_engine.BY_SLUG.get(preset)
    impl = chosen.implementation if chosen else protocol
    db.add(Indexer(name=name or (chosen.name if chosen else ""), url=url or (chosen.url if chosen else ""), api_key=api_key or None,
                   protocol=impl if impl in ("torznab", "newznab") else "native", implementation=impl, preset=preset or None, enabled=True))
    db.commit()
    return RedirectResponse("/ui/indexers", status_code=303)


@router.post("/ui/indexers/{indexer_id}/delete", dependencies=ADMIN)
def ui_delete_indexer(indexer_id: int, db: Session = Depends(get_db)):
    indexer = db.get(Indexer, indexer_id)
    if indexer:
        db.delete(indexer)
        db.commit()
    return RedirectResponse("/ui/indexers", status_code=303)


# --- Movies -----------------------------------------------------------------

@router.get("/library", response_class=HTMLResponse, dependencies=USER)
async def library(request: Request, q: str | None = None, filter: str = "all", db: Session = Depends(get_db)):
    all_movies = library_service.merged_movies(db)  # The Den's rows + what the Plex scan found
    downloading_ids = {m["id"] for m in all_movies if m["downloading"]}
    counts = {
        "total": len(all_movies),
        "have": sum(1 for m in all_movies if m["available"]),
        "missing": sum(1 for m in all_movies if not m["available"]),
        "downloading": len(downloading_ids),
        "plex": sum(1 for m in all_movies if m["on_plex"]),
        "plex_only": sum(1 for m in all_movies if m["source"] == "plex"),
        "tracked": sum(1 for m in all_movies if m["id"]),
        "upgradable": sum(1 for m in all_movies if m.get("upgradable")),
    }
    if filter == "missing":
        movies = [m for m in all_movies if not m["available"]]
    elif filter == "have":
        movies = [m for m in all_movies if m["available"]]
    elif filter == "plex":
        movies = [m for m in all_movies if m["on_plex"]]
    elif filter == "upgradable":
        movies = [m for m in all_movies if m.get("upgradable")]
    else:
        filter, movies = "all", all_movies
    candidates = None
    if q:
        try:
            candidates = await tmdb.search_movie(q, settings_module.effective(db).tmdb_api_key)
        except Exception:
            candidates = []  # unconfigured/invalid TMDB key: show "nothing matched", not a 500
    return templates.TemplateResponse(
        "library.html",
        {
            "request": request, "movies": movies, "counts": counts, "filter": filter,
            "downloading_ids": downloading_ids, "library_tmdb_ids": {m["tmdb_id"] for m in all_movies if m["tmdb_id"]},
            "query": q, "candidates": candidates, "active_nav": "movies",
        },
    )


@router.post("/ui/movies", dependencies=ADMIN)
async def ui_add_movie(
    tmdb_id: int = Form(...),
    title: str = Form(...),
    year: str = Form(""),
    overview: str = Form(""),
    poster_path: str = Form(""),
    db: Session = Depends(get_db),
):
    if not db.query(Movie).filter(Movie.tmdb_id == tmdb_id).first():
        if not poster_path or poster_path.startswith("/api/"):
            # Coming from a Plex-only card: fetch the TMDB poster rather than storing our proxy URL.
            try:
                details = await tmdb.movie_details(tmdb_id, settings_module.effective(db).tmdb_api_key)
            except Exception:
                details = None
            poster_path = (details or {}).get("poster_path") or ""
            overview = overview or (details or {}).get("overview") or ""
        db.add(
            Movie(
                tmdb_id=tmdb_id,
                title=title,
                year=int(year) if year.isdigit() else None,
                overview=overview or None,
                poster_path=poster_path or None,
            )
        )
        db.commit()
    return RedirectResponse("/library", status_code=303)


@router.post("/ui/movies/{movie_id}/delete", dependencies=ADMIN)
def ui_delete_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if movie:
        db.delete(movie)
        db.commit()
    return RedirectResponse("/library", status_code=303)


@router.get("/ui/movies/{movie_id}/candidates", response_class=HTMLResponse, dependencies=ADMIN)
async def ui_movie_candidates(movie_id: int, request: Request, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")
    query = movie_query(movie)
    profile = profile_for(db, movie.quality_profile_id)
    candidates = await scored_candidates(db, query, profile)
    return templates.TemplateResponse(
        "candidates.html",
        {
            "request": request,
            "heading": f"{movie.title} ({movie.year})",
            "grab_action": f"/ui/movies/{movie.id}/grab",
            "back_url": "/library",
            "candidates": candidates,
            "active_nav": "movies",
        },
    )


@router.post("/ui/movies/{movie_id}/grab", dependencies=ADMIN)
async def ui_grab_movie(
    movie_id: int,
    download_url: str = Form(...),
    release_title: str = Form(...),
    db: Session = Depends(get_db),
):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")
    try:
        await do_grab_movie(db, movie, download_url, release_title)
    except Exception as exc:
        raise HTTPException(502, f"Failed to send to download client: {exc}")
    return RedirectResponse("/ui/downloads", status_code=303)


# --- TV -----------------------------------------------------------------

@router.get("/tv", response_class=HTMLResponse, dependencies=USER)
async def tv_library(request: Request, q: str | None = None, filter: str = "all", db: Session = Depends(get_db)):
    all_rows = library_service.merged_series(db)  # The Den's series + what the Plex scan found
    if filter == "missing":
        rows = [r for r in all_rows if not r["available"]]
    elif filter == "have":
        rows = [r for r in all_rows if r["available"]]
    elif filter == "plex":
        rows = [r for r in all_rows if r["on_plex"]]
    else:
        filter, rows = "all", all_rows
    candidates = None
    if q:
        try:
            candidates = await tvmaze.search_tv(q)
        except Exception:
            candidates = []
    return templates.TemplateResponse(
        "tv.html",
        {
            "request": request, "series": rows, "query": q, "candidates": candidates, "filter": filter,
            "counts": {"total": len(all_rows), "plex": sum(1 for r in all_rows if r["on_plex"]), "plex_only": sum(1 for r in all_rows if r["source"] == "plex"), "tracked": sum(1 for r in all_rows if r["id"])},
            "episodes_total": sum(r["total"] for r in all_rows), "episodes_have": sum(r["have"] for r in all_rows),
            "library_tvmaze_ids": {r["tvmaze_id"] for r in all_rows if r["tvmaze_id"]}, "active_nav": "tv",
        },
    )


@router.post("/ui/series", dependencies=ADMIN)
async def ui_add_series(
    tvmaze_id: int = Form(...),
    title: str = Form(...),
    year: str = Form(""),
    overview: str = Form(""),
    poster_path: str = Form(""),
    tmdb_id: str = Form(""),
    db: Session = Depends(get_db),
):
    if not db.query(Series).filter(Series.tvmaze_id == tvmaze_id).first():
        series = Series(
            tvmaze_id=tvmaze_id,
            tmdb_id=int(tmdb_id) if tmdb_id.isdigit() else None,
            title=title,
            year=int(year) if year.isdigit() else None,
            overview=overview or None,
            poster_path=poster_path or None,
        )
        db.add(series)
        db.commit()
        db.refresh(series)
        for ep in await tvmaze.get_tv_episodes(tvmaze_id):
            db.add(Episode(series_id=series.id, **ep))
        db.commit()
    return RedirectResponse("/tv", status_code=303)


@router.post("/ui/series/{series_id}/delete", dependencies=ADMIN)
def ui_delete_series(series_id: int, db: Session = Depends(get_db)):
    series = db.get(Series, series_id)
    if series:
        db.query(Episode).filter(Episode.series_id == series_id).delete()
        db.delete(series)
        db.commit()
    return RedirectResponse("/tv", status_code=303)


@router.get("/ui/series/{series_id}", response_class=HTMLResponse, dependencies=USER)
def ui_series_detail(series_id: int, request: Request, db: Session = Depends(get_db)):
    series = db.get(Series, series_id)
    if not series:
        raise HTTPException(404, "Series not found")
    episodes = (
        db.query(Episode)
        .filter(Episode.series_id == series_id)
        .order_by(Episode.season_number, Episode.episode_number)
        .all()
    )
    profile = profile_for(db, series.quality_profile_id)
    upgradable_ids = {e.id for e in episodes if e.has_file and profile and is_upgradable(e.file_quality, e.file_score, profile)}
    seasons: list[dict] = []
    for e in episodes:
        if not seasons or seasons[-1]["number"] != e.season_number:
            seasons.append({"number": e.season_number, "episodes": [], "have": 0, "total": 0, "monitored": False})
        seasons[-1]["episodes"].append(e)
        seasons[-1]["total"] += 1
        seasons[-1]["have"] += 1 if e.has_file else 0
        seasons[-1]["monitored"] = seasons[-1]["monitored"] or bool(e.monitored)
    return templates.TemplateResponse(
        "series_detail.html",
        {
            "request": request, "series": series, "seasons": seasons,
            "have": sum(s["have"] for s in seasons), "total": len(episodes),
            "upgradable_ids": upgradable_ids,
            "today": date.today().isoformat(), "active_nav": "tv",
        },
    )


@router.get("/ui/episodes/{episode_id}/candidates", response_class=HTMLResponse, dependencies=ADMIN)
async def ui_episode_candidates(episode_id: int, request: Request, db: Session = Depends(get_db)):
    episode = db.get(Episode, episode_id)
    if not episode:
        raise HTTPException(404, "Episode not found")
    series = db.get(Series, episode.series_id)
    query = episode_query(series, episode)
    profile = profile_for(db, series.quality_profile_id)
    candidates = await scored_candidates(db, query, profile)
    return templates.TemplateResponse(
        "candidates.html",
        {
            "request": request,
            "heading": f"{series.title} S{episode.season_number:02d}E{episode.episode_number:02d}",
            "grab_action": f"/ui/episodes/{episode.id}/grab",
            "back_url": f"/ui/series/{series.id}",
            "candidates": candidates,
            "active_nav": "tv",
        },
    )


@router.get("/ui/series/{series_id}/seasons/{season_number}/candidates", response_class=HTMLResponse, dependencies=ADMIN)
async def ui_season_candidates(series_id: int, season_number: int, request: Request, db: Session = Depends(get_db)):
    series = db.get(Series, series_id)
    if not series:
        raise HTTPException(404, "Series not found")
    candidates = await season_candidates(db, series, season_number, profile_for(db, series.quality_profile_id))
    return templates.TemplateResponse(
        "candidates.html",
        {
            "request": request,
            "heading": f"{series.title} S{season_number:02d} (season pack)",
            "grab_action": f"/ui/series/{series.id}/seasons/{season_number}/grab",
            "back_url": f"/ui/series/{series.id}",
            "candidates": candidates,
            "active_nav": "tv",
        },
    )


@router.post("/ui/series/{series_id}/seasons/{season_number}/grab", dependencies=ADMIN)
async def ui_grab_season(series_id: int, season_number: int, download_url: str = Form(...), release_title: str = Form(...), db: Session = Depends(get_db)):
    series = db.get(Series, series_id)
    if not series:
        raise HTTPException(404, "Series not found")
    try:
        await do_grab_season(db, series, season_number, download_url, release_title)
    except Exception as exc:
        raise HTTPException(502, f"Failed to send to download client: {exc}")
    return RedirectResponse("/ui/downloads", status_code=303)


@router.post("/ui/series/{series_id}/seasons/{season_number}/{action}", dependencies=ADMIN)
async def ui_season_action(series_id: int, season_number: int, action: str, db: Session = Depends(get_db)):
    """monitor | unmonitor | mark-have | search, from the season header on the series page."""
    series = db.get(Series, series_id)
    if not series:
        raise HTTPException(404, "Series not found")
    episodes = db.query(Episode).filter(Episode.series_id == series_id, Episode.season_number == season_number).all()
    if action in ("monitor", "unmonitor"):
        for e in episodes:
            e.monitored = action == "monitor"
        db.commit()
    elif action == "mark-have":
        for e in episodes:
            e.has_file = True
        db.commit()
    elif action == "search":
        await automation.search_season(db, series, season_number)
    else:
        raise HTTPException(404, "Unknown season action")
    return RedirectResponse(f"/ui/series/{series_id}", status_code=303)


@router.post("/ui/episodes/{episode_id}/grab", dependencies=ADMIN)
async def ui_grab_episode(
    episode_id: int,
    download_url: str = Form(...),
    release_title: str = Form(...),
    db: Session = Depends(get_db),
):
    episode = db.get(Episode, episode_id)
    if not episode:
        raise HTTPException(404, "Episode not found")
    try:
        await do_grab_episode(db, episode, download_url, release_title)
    except Exception as exc:
        raise HTTPException(502, f"Failed to send to download client: {exc}")
    return RedirectResponse("/ui/downloads", status_code=303)


# --- Downloads -----------------------------------------------------------------

@router.get("/ui/downloads", response_class=HTMLResponse, dependencies=ADMIN)
def ui_downloads(request: Request, db: Session = Depends(get_db)):
    # Live torrents are fetched by the page's own JS from /torrents. What's rendered
    # here is the history: records whose torrent is gone (imported + reaped, or failed).
    live_hashes = {t.info_hash for t in torrent_engine.list()}
    records = (
        db.query(DownloadRecord)
        .filter(DownloadRecord.status.in_(["imported", "failed", "completed"]))
        .order_by(DownloadRecord.id.desc())
        .limit(50)
        .all()
    )
    history = []
    for d in records:
        if d.info_hash and d.info_hash in live_hashes:
            continue
        label = None
        if d.movie_id and (movie := db.get(Movie, d.movie_id)):
            label = f"{movie.title} ({movie.year})" if movie.year else movie.title
        elif d.episode_id and (episode := db.get(Episode, d.episode_id)):
            series = db.get(Series, episode.series_id)
            label = f"{series.title if series else '?'} S{episode.season_number:02d}E{episode.episode_number:02d}"
        history.append({"release_title": d.release_title, "status": d.status, "label": label, "failure_reason": d.failure_reason})
    entries = [
        {"id": b.id, "release_title": b.release_title, "reason": b.reason, "expires_at": b.expires_at.isoformat() if b.expires_at else None}
        for b in blocklist.active(db)
    ]
    return templates.TemplateResponse(
        "downloads.html", {"request": request, "history": history, "blocklist": entries, "active_nav": "downloads", "unmatched_count": len(_unmatched_records(db))}
    )


@router.post("/ui/downloads/blocklist/{entry_id}/delete", dependencies=ADMIN)
def ui_delete_blocklist(entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(BlocklistEntry, entry_id)
    if entry:
        db.delete(entry)
        db.commit()
    return RedirectResponse("/ui/downloads", status_code=303)


@router.post("/ui/downloads/{download_id}/check", dependencies=ADMIN)
async def ui_check_download(download_id: int, db: Session = Depends(get_db)):
    record = db.get(DownloadRecord, download_id)
    if not record:
        raise HTTPException(404, "Download not found")
    try:
        await check_and_import(db, record)
    except Exception as exc:
        raise HTTPException(502, f"Failed to reach download client: {exc}")
    return RedirectResponse("/ui/downloads", status_code=303)


# --- Calendar -----------------------------------------------------------------

@router.get("/calendar", response_class=HTMLResponse, dependencies=USER)
def calendar(request: Request, month: str | None = None, db: Session = Depends(get_db)):
    today = date.today()
    try:
        year, mon = (int(x) for x in (month or "").split("-"))
        first = date(year, mon, 1)
    except (TypeError, ValueError):
        first = date(today.year, today.month, 1)
    last = date(first.year, first.month, monthrange(first.year, first.month)[1])
    prev_first = (first - timedelta(days=1)).replace(day=1)
    next_first = (last + timedelta(days=1))
    grid_start = first - timedelta(days=first.weekday())  # Monday
    grid_end = last + timedelta(days=6 - last.weekday())

    series_titles = {s.id: s.title for s in db.query(Series.id, Series.title)}

    def item(e: Episode) -> dict:
        tone = "available" if e.has_file else ("pending" if e.air_date > today.isoformat() else "partial")
        return {
            "series_id": e.series_id, "series": series_titles.get(e.series_id, "?"), "season": e.season_number,
            "episode": e.episode_number, "title": e.title, "air_date": e.air_date, "tone": tone,
        }

    in_grid = (
        db.query(Episode)
        .filter(Episode.air_date >= grid_start.isoformat(), Episode.air_date <= grid_end.isoformat())
        .order_by(Episode.air_date, Episode.series_id, Episode.season_number, Episode.episode_number)
        .all()
    )
    by_day: dict[str, list[dict]] = {}
    for e in in_grid:
        by_day.setdefault(e.air_date, []).append(item(e))

    weeks, day = [], grid_start
    while day <= grid_end:
        week = []
        for _ in range(7):
            # "episodes", not "items": a dict key named items would shadow dict.items in Jinja.
            week.append({"date": day, "in_month": day.month == first.month, "is_today": day == today, "episodes": by_day.get(day.isoformat(), [])})
            day += timedelta(days=1)
        weeks.append(week)

    month_items = [i for k, items in by_day.items() for i in items if first.isoformat() <= k <= last.isoformat()]
    month_counts = {
        "have": sum(1 for i in month_items if i["tone"] == "available"),
        "missing": sum(1 for i in month_items if i["tone"] == "partial"),
        "upcoming": sum(1 for i in month_items if i["tone"] == "pending"),
    }

    agenda_missing = [
        item(e) for e in db.query(Episode)
        .filter(Episode.has_file == False, Episode.air_date.isnot(None), Episode.air_date <= today.isoformat())  # noqa: E712
        .order_by(Episode.air_date.desc()).limit(20)
    ]
    horizon = (today + timedelta(days=14)).isoformat()
    agenda_upcoming = [
        item(e) for e in db.query(Episode)
        .filter(Episode.air_date > today.isoformat(), Episode.air_date <= horizon)
        .order_by(Episode.air_date).limit(20)
    ]
    missing_movies = db.query(Movie).filter(Movie.has_file == False).order_by(Movie.id.desc()).limit(12).all()  # noqa: E712

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request, "weeks": weeks, "month_label": first.strftime("%B %Y"),
            "prev_month": prev_first.strftime("%Y-%m"), "prev_label": prev_first.strftime("%b"),
            "next_month": next_first.strftime("%Y-%m"), "next_label": next_first.strftime("%b"),
            "is_current_month": first.month == today.month and first.year == today.year,
            "month_counts": month_counts, "agenda_missing": agenda_missing, "agenda_upcoming": agenda_upcoming,
            "missing_movies": missing_movies, "active_nav": "calendar",
        },
    )


# --- Settings -----------------------------------------------------------------

@router.get("/ui/settings", response_class=HTMLResponse, dependencies=ADMIN)
def ui_settings(request: Request, db: Session = Depends(get_db)):
    row = settings_module.get_row(db)
    s = settings_module.effective(db)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "s": s,
            "has_tmdb_api_key": bool(row.tmdb_api_key),
            "has_discord_webhook": bool(row.discord_webhook_url),
            "state_dir": config.STATE_DIR,
            "saved": request.query_params.get("saved") == "1",
            "notice": request.query_params.get("notice"),
            "error": request.query_params.get("error"),
            "plex_last_scan_at": row.plex_last_scan_at,
            "plex_last_scan_result": row.plex_last_scan_result,
            "active_nav": "settings",
        },
    )


def _int_or_none(value: str) -> int | None:
    return int(value) if value.strip().isdigit() else None


def _float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


@router.post("/ui/settings", dependencies=ADMIN)
def ui_save_settings(
    tmdb_api_key: str = Form(""),
    movies_root: str = Form(""),
    tv_root: str = Form(""),
    automation_interval_seconds: str = Form(""),
    discord_webhook_url: str = Form(""),
    downloads_root: str = Form(""),
    torrent_port: str = Form(""),
    download_rate_limit_kib: str = Form(""),
    upload_rate_limit_kib: str = Form(""),
    seed_ratio_limit: str = Form(""),
    seed_time_limit_minutes: str = Form(""),
    request_movie_limit: str = Form(""),
    request_series_limit: str = Form(""),
    request_limit_days: str = Form(""),
    flaresolverr_url: str = Form(""),
    db: Session = Depends(get_db),
):
    row = settings_module.get_row(db)
    old = settings_module.effective(db)
    row.flaresolverr_url = flaresolverr_url.strip() or None
    row.request_movie_limit = _int_or_none(request_movie_limit)
    row.request_series_limit = _int_or_none(request_series_limit)
    row.request_limit_days = _int_or_none(request_limit_days) or None

    # Secret fields: only overwrite if the user actually typed something new.
    if tmdb_api_key:
        row.tmdb_api_key = tmdb_api_key
    if discord_webhook_url:
        row.discord_webhook_url = discord_webhook_url

    # Non-secret fields: always take the submitted value (blank means "use the default").
    row.movies_root = movies_root or None
    row.tv_root = tv_root or None
    row.automation_interval_seconds = _int_or_none(automation_interval_seconds)
    row.downloads_root = downloads_root or None
    row.torrent_port = _int_or_none(torrent_port)
    row.download_rate_limit_kib = _int_or_none(download_rate_limit_kib)
    row.upload_rate_limit_kib = _int_or_none(upload_rate_limit_kib)
    row.seed_ratio_limit = _float_or_none(seed_ratio_limit)
    row.seed_time_limit_minutes = _int_or_none(seed_time_limit_minutes)

    db.commit()
    apply_runtime_changes(old, settings_module.effective(db))
    return RedirectResponse("/ui/settings?saved=1", status_code=303)


@router.post("/ui/settings/accounts", dependencies=ADMIN)
def ui_save_accounts(request: Request, require_signin: str = Form(""), db: Session = Depends(get_db)):
    """Settings -> Accounts: require sign-in everywhere (overrides the AUTH_REQUIRED env var)."""
    want = require_signin == "1"
    if want and getattr(request.state, "user", None) is None:
        return RedirectResponse("/ui/settings?error=Sign+in+as+an+admin+first,+or+you%27d+lock+yourself+out#accounts", status_code=303)
    row = settings_module.get_row(db)
    row.auth_required = want
    db.commit()
    auth.set_required_override(want)
    return RedirectResponse("/ui/settings?saved=1#accounts", status_code=303)


@router.get("/ui/downloads/unmatched", response_class=HTMLResponse, dependencies=ADMIN)
def ui_downloads_unmatched(request: Request, db: Session = Depends(get_db)):
    entries = [e for r in _unmatched_records(db) if (e := _unmatched_entry(db, r)) is not None]
    return templates.TemplateResponse("manual_import.html", {"request": request, "entries": entries, "active_nav": "downloads"})


@router.post("/ui/downloads/unmatched/{download_id}/assign", dependencies=ADMIN)
def ui_assign_unmatched(download_id: int, file: str = Form(...), kind: str = Form(...), target_id: int = Form(...), db: Session = Depends(get_db)):
    _assign_download_action(download_id, AssignBody(file=file, kind=kind, id=target_id), db)
    return RedirectResponse("/ui/downloads/unmatched", status_code=303)


@router.post("/ui/downloads/unmatched/{download_id}/import-as-is", dependencies=ADMIN)
def ui_import_as_is_unmatched(download_id: int, file: str = Form(...), root: str = Form(...), db: Session = Depends(get_db)):
    _import_as_is_action(download_id, ImportAsIsBody(file=file, root=root), db)
    return RedirectResponse("/ui/downloads/unmatched", status_code=303)
