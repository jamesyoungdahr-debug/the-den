from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import settings as settings_module
from app import tmdb
from app.candidates import scored_candidates
from app.deps import get_db
from app.grabber import grab_movie as do_grab_movie
from app.models import Movie, QualityProfile
from app.schemas import DownloadRecordOut, GrabRequest, MovieCreate, MovieOut, ScoredReleaseOut

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search-tmdb")
async def search_tmdb(q: str, db: Session = Depends(get_db)):
    api_key = settings_module.effective(db).tmdb_api_key
    return await tmdb.search_movie(q, api_key)


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
    try:
        return await do_grab_movie(db, movie, payload.download_url, payload.release_title)
    except Exception as exc:
        raise HTTPException(502, f"Failed to send to download client: {exc}")
