import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import auth
from app import torznab
from app.deps import get_db
from app.models import Indexer
from app.schemas import ReleaseOut

router = APIRouter(tags=["search"], dependencies=[Depends(auth.require_admin)])


@router.get("/search", response_model=list[ReleaseOut])
async def manual_search(q: str, db: Session = Depends(get_db)):
    indexers = db.query(Indexer).filter(Indexer.enabled == True).all()  # noqa: E712

    async def safe_search(indexer: Indexer):
        try:
            return await torznab.search(indexer.url, indexer.api_key, q, indexer.name)
        except Exception as exc:
            return exc  # swallow single-indexer failures, don't fail the whole search

    results_per_indexer = await asyncio.gather(*(safe_search(i) for i in indexers))

    releases = []
    for result in results_per_indexer:
        if isinstance(result, list):
            releases.extend(result)
    releases.sort(key=lambda r: r.seeders or 0, reverse=True)
    return releases
