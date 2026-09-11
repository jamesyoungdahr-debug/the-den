from calendar import monthrange
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import auth, config
from app import settings as settings_module
from app import tmdb, torznab, tvmaze
from app.candidates import scored_candidates
from app.deps import get_db
from app.download_check import check_and_import
from app.grabber import grab_episode as do_grab_episode
from app.grabber import grab_movie as do_grab_movie
from app.models import DownloadRecord, Episode, Indexer, Movie, QualityProfile, Series
from app.routers.api_settings import apply_runtime_changes
from app.templating import templates
from app.torrent import engine as torrent_engine

router = APIRouter(tags=["ui"])

# Route guards (see app/auth.py): pages anyone signed in may see vs. admin plumbing.
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
        enabled = [i for i in indexers if i.enabled]
        gathered = []
        for i in enabled:
            try:
                gathered.extend(await torznab.search(i.url, i.api_key, q, i.name))
            except Exception:
                pass  # a broken indexer shouldn't blank out the whole search
        gathered.sort(key=lambda r: r.seeders or 0, reverse=True)
        results = gathered
    return templates.TemplateResponse(
        "indexers.html",
        {"request": request, "indexers": indexers, "query": q, "results": results, "active_nav": "indexers"},
    )


@router.post("/ui/indexers", dependencies=ADMIN)
def ui_create_indexer(
    name: str = Form(...),
    url: str = Form(...),
    api_key: str = Form(""),
    protocol: str = Form("torznab"),
    db: Session = Depends(get_db),
):
    db.add(Indexer(name=name, url=url, api_key=api_key or None, protocol=protocol, enabled=True))
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
    all_movies = db.query(Movie).order_by(Movie.id.desc()).all()
    downloading_ids = _downloading_movie_ids(db)
    counts = {
        "total": len(all_movies),
        "have": sum(1 for m in all_movies if m.has_file),
        "missing": sum(1 for m in all_movies if not m.has_file),
        "downloading": len(downloading_ids),
    }
    if filter == "missing":
        movies = [m for m in all_movies if not m.has_file]
    elif filter == "have":
        movies = [m for m in all_movies if m.has_file]
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
            "downloading_ids": downloading_ids, "library_tmdb_ids": {m.tmdb_id for m in all_movies},
            "query": q, "candidates": candidates, "active_nav": "movies",
        },
    )


@router.post("/ui/movies", dependencies=ADMIN)
def ui_add_movie(
    tmdb_id: int = Form(...),
    title: str = Form(...),
    year: str = Form(""),
    overview: str = Form(""),
    poster_path: str = Form(""),
    db: Session = Depends(get_db),
):
    if not db.query(Movie).filter(Movie.tmdb_id == tmdb_id).first():
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
    query = f"{movie.title} {movie.year}" if movie.year else movie.title
    profile = db.get(QualityProfile, movie.quality_profile_id) if movie.quality_profile_id else db.query(QualityProfile).first()
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
async def tv_library(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    all_series = db.query(Series).order_by(Series.id.desc()).all()
    rows = _series_rows(db, all_series)
    candidates = None
    if q:
        try:
            candidates = await tvmaze.search_tv(q)
        except Exception:
            candidates = []
    return templates.TemplateResponse(
        "tv.html",
        {
            "request": request, "series": rows, "query": q, "candidates": candidates,
            "episodes_total": sum(r["total"] for r in rows), "episodes_have": sum(r["have"] for r in rows),
            "library_tvmaze_ids": {s.tvmaze_id for s in all_series}, "active_nav": "tv",
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
    seasons: list[dict] = []
    for e in episodes:
        if not seasons or seasons[-1]["number"] != e.season_number:
            seasons.append({"number": e.season_number, "episodes": [], "have": 0, "total": 0})
        seasons[-1]["episodes"].append(e)
        seasons[-1]["total"] += 1
        seasons[-1]["have"] += 1 if e.has_file else 0
    return templates.TemplateResponse(
        "series_detail.html",
        {
            "request": request, "series": series, "seasons": seasons,
            "have": sum(s["have"] for s in seasons), "total": len(episodes),
            "today": date.today().isoformat(), "active_nav": "tv",
        },
    )


@router.get("/ui/episodes/{episode_id}/candidates", response_class=HTMLResponse, dependencies=ADMIN)
async def ui_episode_candidates(episode_id: int, request: Request, db: Session = Depends(get_db)):
    episode = db.get(Episode, episode_id)
    if not episode:
        raise HTTPException(404, "Episode not found")
    series = db.get(Series, episode.series_id)
    query = f"{series.title} S{episode.season_number:02d}E{episode.episode_number:02d}"
    profile = db.get(QualityProfile, series.quality_profile_id) if series.quality_profile_id else db.query(QualityProfile).first()
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
        history.append({"release_title": d.release_title, "status": d.status, "label": label})
    return templates.TemplateResponse(
        "downloads.html", {"request": request, "history": history, "active_nav": "downloads"}
    )


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
    db: Session = Depends(get_db),
):
    row = settings_module.get_row(db)
    old = settings_module.effective(db)

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
