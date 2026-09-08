from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import qbittorrent, tmdb
from app.candidates import scored_candidates
from app.deps import get_db
from app.models import DownloadRecord, Movie, QualityProfile
from app.schemas import DownloadRecordOut, GrabRequest, MovieCreate, MovieOut, ScoredReleaseOut

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search-tmdb")
async def search_tmdb(q: str):
    return await tmdb.search_movie(q)


@router.get("", response_model=list[MovieOut])
def list_movies(db: Session = Depends(get_db)):
    return db.query(Movie).all()


@router.post("", response_model=MovieOut, status_code=201)
def add_movie(payload: MovieCreate, db: Session = Depends(get_db)):
    if db.query(Movie).filter(Movie.tmdb_id == payload.tmdb_id).first():
        raise HTTPException(400, "Movie already in library")
    movie = Movie(**payload.model_dump())
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie


@router.delete("/{movie_id}", status_code=204)
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if movie:
        db.delete(movie)
        db.commit()


@router.get("/{movie_id}/candidates", response_model=list[ScoredReleaseOut])
async def movie_candidates(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")

    query = f"{movie.title} {movie.year}" if movie.year else movie.title
    profile = db.get(QualityProfile, movie.quality_profile_id) if movie.quality_profile_id else db.query(QualityProfile).first()
    return await scored_candidates(db, query, profile)


@router.post("/{movie_id}/grab", response_model=DownloadRecordOut)
async def grab_movie(movie_id: int, payload: GrabRequest, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")

    category = f"the-den-movie-{movie_id}"
    try:
        await qbittorrent.add_torrent(payload.download_url, category)
    except Exception as exc:
        raise HTTPException(502, f"Failed to send to download client: {exc}")

    record = DownloadRecord(
        movie_id=movie_id,
        release_title=payload.release_title,
        download_url=payload.download_url,
        category=category,
        status="queued",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
