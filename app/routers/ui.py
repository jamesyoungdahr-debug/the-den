from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import importer, qbittorrent, tmdb, torznab
from app.deps import get_db
from app.models import DownloadRecord, Indexer, Movie, QualityProfile
from app.parser import parse_quality
from app.scoring import best_release

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
        "index.html", {"request": request, "indexers": indexers, "query": q, "results": results}
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


@router.get("/library", response_class=HTMLResponse)
async def library(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    movies = db.query(Movie).all()
    candidates = await tmdb.search_movie(q) if q else None
    return templates.TemplateResponse(
        "library.html", {"request": request, "movies": movies, "query": q, "candidates": candidates}
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

    indexers = db.query(Indexer).filter(Indexer.enabled == True).all()  # noqa: E712
    query = f"{movie.title} {movie.year}" if movie.year else movie.title
    releases = []
    for indexer in indexers:
        try:
            releases.extend(await torznab.search(indexer.url, indexer.api_key, query, indexer.name))
        except Exception:
            pass

    profile = db.get(QualityProfile, movie.quality_profile_id) if movie.quality_profile_id else db.query(QualityProfile).first()
    best = best_release(releases, profile) if profile else None

    candidates = [
        {
            "title": r.title,
            "download_url": r.download_url,
            "indexer_name": r.indexer_name,
            "seeders": r.seeders,
            "quality": parse_quality(r.title),
            "is_best": r is best,
        }
        for r in releases
    ]
    candidates.sort(key=lambda r: (not r["is_best"], -(r["seeders"] or 0)))
    return templates.TemplateResponse(
        "candidates.html", {"request": request, "movie": movie, "candidates": candidates}
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
    category = f"the-den-movie-{movie_id}"
    try:
        await qbittorrent.add_torrent(download_url, category)
    except Exception as exc:
        raise HTTPException(502, f"Failed to send to download client: {exc}")
    db.add(
        DownloadRecord(
            movie_id=movie_id, release_title=release_title, download_url=download_url,
            category=category, status="queued",
        )
    )
    db.commit()
    return RedirectResponse("/ui/downloads", status_code=303)


@router.get("/ui/downloads", response_class=HTMLResponse)
def ui_downloads(request: Request, db: Session = Depends(get_db)):
    downloads = db.query(DownloadRecord).all()
    return templates.TemplateResponse("downloads.html", {"request": request, "downloads": downloads})


@router.post("/ui/downloads/{download_id}/check")
async def ui_check_download(download_id: int, db: Session = Depends(get_db)):
    record = db.get(DownloadRecord, download_id)
    if not record:
        raise HTTPException(404, "Download not found")
    if record.status != "imported":
        try:
            info = await qbittorrent.get_by_category(record.category)
        except Exception as exc:
            raise HTTPException(502, f"Failed to reach download client: {exc}")
        if info is None:
            record.status = "queued"
        elif info.get("progress", 0) >= 1.0:
            movie = db.get(Movie, record.movie_id)
            if importer.import_finished_download(info, movie):
                movie.has_file = True
                record.status = "imported"
            else:
                record.status = "completed"
        else:
            record.status = "downloading"
        db.commit()
    return RedirectResponse("/ui/downloads", status_code=303)
