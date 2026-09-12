from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import auth
from app import indexers as indexer_engine
from app.deps import get_db
from app.schemas import ReleaseOut

router = APIRouter(tags=["search"], dependencies=[Depends(auth.require_admin)])


@router.get("/search", response_model=list[ReleaseOut])
async def manual_search(q: str, db: Session = Depends(get_db)):
    """Every enabled indexer at once (Torznab, Newznab and the native public trackers);
    a failing indexer is skipped rather than failing the whole search."""
    releases = await indexer_engine.search_all(db, q)
    releases.sort(key=lambda r: r.seeders or 0, reverse=True)
    return releases
