"""JSON twins of the Movies and TV pages: the library merged with the Plex scan, for
the companion apps (see app.library_service for the entry shape)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import auth, library_service
from app.deps import get_db

router = APIRouter(prefix="/api/library", tags=["library"], dependencies=[Depends(auth.require_user)])


@router.get("/movies")
def api_library_movies(db: Session = Depends(get_db)):
    return library_service.merged_movies(db)


@router.get("/series")
def api_library_series(db: Session = Depends(get_db)):
    return library_service.merged_series(db)
