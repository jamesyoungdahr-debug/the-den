from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import torznab
from app.deps import get_db
from app.models import Indexer
from app.schemas import IndexerCreate, IndexerOut

router = APIRouter(prefix="/indexers", tags=["indexers"])


@router.get("", response_model=list[IndexerOut])
def list_indexers(db: Session = Depends(get_db)):
    return db.query(Indexer).all()


@router.post("", response_model=IndexerOut, status_code=201)
def create_indexer(payload: IndexerCreate, db: Session = Depends(get_db)):
    indexer = Indexer(**payload.model_dump())
    db.add(indexer)
    db.commit()
    db.refresh(indexer)
    return indexer


@router.get("/{indexer_id}/test")
async def test_indexer(indexer_id: int, db: Session = Depends(get_db)):
    indexer = db.get(Indexer, indexer_id)
    if not indexer:
        raise HTTPException(404, "Indexer not found")
    try:
        return await torznab.test_connection(indexer.url, indexer.api_key)
    except Exception as exc:
        raise HTTPException(502, f"Connection test failed: {exc}")


@router.delete("/{indexer_id}", status_code=204)
def delete_indexer(indexer_id: int, db: Session = Depends(get_db)):
    indexer = db.get(Indexer, indexer_id)
    if not indexer:
        raise HTTPException(404, "Indexer not found")
    db.delete(indexer)
    db.commit()
