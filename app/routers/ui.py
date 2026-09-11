from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import config
from app import settings as settings_module
from app import tmdb, torznab, tvmaze
from app.candidates import scored_candidates
from app.deps import get_db
from app.download_check import check_and_import
from app.grabber import grab_episode as do_grab_episode
from app.grabber import grab_movie as do_grab_movie
from app.models import DownloadRecord, Episode, Indexer, Movie, QualityProfile, Series
from app.routers.api_settings import apply_runtime_changes
from app.torrent import engine as torrent_engine

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, q: str | None = None, db: Session = Depends(get_db)):
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
        "index.html",
        {"request": request, "indexers": indexers, "query": q, "results": results, "active_nav": "search"},
    )


@router.post("/ui/indexers")
def ui_create_indexer(
    name: str = Form(...),
    url: str = Form(...),
    api_key: str = Form(""),
    protocol: str = Form("torznab"),
    db: Session = Depends(get_db),
):
    db.add(Indexer(name=name, url=url, api_key=api_key or None, protocol=protocol, enabled=True))
    db.commit()
    return RedirectResponse("/", status_code=303)


@router.post("/ui/indexers/{indexer_id}/delete")
def ui_delete_indexer(indexer_id: int, db: Session = Depends(get_db)):
    indexer = db.get(Indexer, indexer_id)
    if indexer:
        db.delete(indexer)
        db.commit()
    return RedirectResponse("/", status_code=303)


# --- Movies -----------------------------------------------------------------

@router.get("/library", response_class=HTMLResponse)
async def library(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    movies = db.query(Movie).all()
    candidates = await tmdb.search_movie(q, settings_module.effective(db).tmdb_api_key) if q else None
    return templates.TemplateResponse(
        "library.html",
        {"request": request, "movies": movies, "query": q, "candidates": candidates, "active_nav": "movies"},
    )


@router.post("/ui/movies")
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


@router.post("/ui/movies/{movie_id}/delete")
def ui_delete_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if movie:
        db.delete(movie)
        db.commit()
    return RedirectResponse("/library", status_code=303)


@router.get("/ui/movies/{movie_id}/candidates", response_class=HTMLResponse)
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
            "candidates": candidates,
            "active_nav": "movies",
        },
    )


@router.post("/ui/movies/{movie_id}/grab")
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

@router.get("/tv", response_class=HTMLResponse)
async def tv_library(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    all_series = db.query(Series).all()
    rows = []
    for s in all_series:
        episodes = db.query(Episode).filter(Episode.series_id == s.id).all()
        rows.append({"series": s, "total": len(episodes), "have": sum(1 for e in episodes if e.has_file)})
    candidates = await tvmaze.search_tv(q) if q else None
    return templates.TemplateResponse(
        "tv.html",
        {"request": request, "series": rows, "query": q, "candidates": candidates, "active_nav": "tv"},
    )


@router.post("/ui/series")
async def ui_add_series(
    tvmaze_id: int = Form(...),
    title: str = Form(...),
    year: str = Form(""),
    overview: str = Form(""),
    poster_path: str = Form(""),
    db: Session = Depends(get_db),
):
    if not db.query(Series).filter(Series.tvmaze_id == tvmaze_id).first():
        series = Series(
            tvmaze_id=tvmaze_id,
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


@router.post("/ui/series/{series_id}/delete")
def ui_delete_series(series_id: int, db: Session = Depends(get_db)):
    series = db.get(Series, series_id)
    if series:
        db.query(Episode).filter(Episode.series_id == series_id).delete()
        db.delete(series)
        db.commit()
    return RedirectResponse("/tv", status_code=303)


@router.get("/ui/series/{series_id}", response_class=HTMLResponse)
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
    return templates.TemplateResponse(
        "series_detail.html",
        {"request": request, "series": series, "episodes": episodes, "active_nav": "tv"}
    )


@router.get("/ui/episodes/{episode_id}/candidates", response_class=HTMLResponse)
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
            "candidates": candidates,
            "active_nav": "tv",
        },
    )


@router.post("/ui/episodes/{episode_id}/grab")
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

@router.get("/ui/downloads", response_class=HTMLResponse)
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


@router.post("/ui/downloads/{download_id}/check")
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

@router.get("/calendar", response_class=HTMLResponse)
def calendar(request: Request, db: Session = Depends(get_db)):
    missing_movies = db.query(Movie).filter(Movie.has_file == False).all()  # noqa: E712

    missing_episodes = []
    for episode in db.query(Episode).filter(Episode.has_file == False).order_by(Episode.air_date).all():
        series = db.get(Series, episode.series_id)
        missing_episodes.append(
            {
                "air_date": episode.air_date,
                "series_title": series.title,
                "season_number": episode.season_number,
                "episode_number": episode.episode_number,
                "title": episode.title,
            }
        )
    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "missing_movies": missing_movies,
            "missing_episodes": missing_episodes,
            "active_nav": "calendar",
        },
    )


# --- Settings -----------------------------------------------------------------

@router.get("/ui/settings", response_class=HTMLResponse)
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


@router.post("/ui/settings")
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
    return RedirectResponse("/ui/settings", status_code=303)
