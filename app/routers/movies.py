from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth
from app import settings as settings_module
from app import tmdb
from app.candidates import movie_query, profile_for, scored_candidates
from app.deps import get_db
from app.grabber import grab_movie as do_grab_movie
from app.models import DownloadRecord, Movie
from app.schemas import DownloadRecordOut, GrabRequest, MovieCreate, MovieOut, ScoredReleaseOut

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search-tmdb", dependencies=[Depends(auth.require_user)])
async def search_tmdb(q: str, db: Session = Depends(get_db)):
    api_key = settings_module.effective(db).tmdb_api_key
    return await tmdb.search_movie(q, api_key)


@router.get("", response_model=list[MovieOut], dependencies=[Depends(auth.require_user)])
def list_movies(db: Session = Depends(get_db)):
    return db.query(Movie).all()


@router.post("", response_model=MovieOut, status_code=201, dependencies=[Depends(auth.require_admin)])
def add_movie(payload: MovieCreate, db: Session = Depends(get_db)):
    if db.query(Movie).filter(Movie.tmdb_id == payload.tmdb_id).first():
        raise HTTPException(400, "Movie already in library")
    movie = Movie(**payload.model_dump())
    db.add(movie)
    try:
        db.commit()
    except IntegrityError:
        # Two concurrent adds for the same tmdb_id both passed the check above --
        # the loser hits the DB's unique constraint instead. Same clean error either way.
        db.rollback()
        raise HTTPException(400, "Movie already in library")
    db.refresh(movie)
    return movie


@router.delete("/{movie_id}", status_code=204, dependencies=[Depends(auth.require_admin)])
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if movie:
        # Mark any in-flight download as failed rather than leaving it pointing at a
        # movie that's about to stop existing -- check_and_import() dereferences
        # record.movie_id unconditionally and has no way to know it's gone.
        db.query(DownloadRecord).filter(
            DownloadRecord.movie_id == movie_id,
            DownloadRecord.status.notin_(["imported", "failed"]),
        ).update({"status": "failed"})
        db.delete(movie)
        db.commit()


@router.get("/{movie_id}/candidates", response_model=list[ScoredReleaseOut], dependencies=[Depends(auth.require_admin)])
async def movie_candidates(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")

    query = movie_query(movie)
    profile = profile_for(db, movie.quality_profile_id)
    return await scored_candidates(db, query, profile)


@router.post("/{movie_id}/grab", response_model=DownloadRecordOut, dependencies=[Depends(auth.require_admin)])
async def grab_movie(movie_id: int, payload: GrabRequest, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")
    try:
        return await do_grab_movie(db, movie, payload.download_url, payload.release_title)
    except Exception as exc:
        raise HTTPException(502, f"Failed to send to download client: {exc}")
