"""Import lists (E1): CRUD and manual sync for auto-adding movies/series from a TMDB
list or a Plex watchlist, mirroring app/routers/notifications.py's shape."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth, import_lists as import_lists_service
from app.deps import get_db
from app.models import ImportList

router = APIRouter(prefix="/api/import-lists", tags=["import-lists"], dependencies=[Depends(auth.require_admin)])

KINDS = ("tmdb_list", "plex_watchlist")


class ImportListIn(BaseModel):
    name: str
    kind: str
    config: dict = {}
    quality_profile_id: int | None = None
    enabled: bool = True


def _out(il: ImportList) -> dict:
    return {
        "id": il.id,
        "name": il.name,
        "kind": il.kind,
        "config": json.loads(il.config or "{}"),
        "quality_profile_id": il.quality_profile_id,
        "enabled": il.enabled,
        "last_synced_at": il.last_synced_at.isoformat() if il.last_synced_at else None,
        "last_result": il.last_result,
    }


def _validate(kind: str, config: dict) -> None:
    if kind not in KINDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown import list kind {kind!r}")
    if kind == "tmdb_list" and not config.get("list_id"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "tmdb_list: list_id is required")


@router.get("")
def list_import_lists(db: Session = Depends(get_db)):
    return [_out(il) for il in db.query(ImportList).order_by(ImportList.id).all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_import_list(body: ImportListIn, db: Session = Depends(get_db)):
    _validate(body.kind, body.config)
    il = ImportList(name=body.name, kind=body.kind, config=json.dumps(body.config), quality_profile_id=body.quality_profile_id, enabled=body.enabled)
    db.add(il)
    db.commit()
    db.refresh(il)
    return _out(il)


@router.put("/{import_list_id}")
def update_import_list(import_list_id: int, body: ImportListIn, db: Session = Depends(get_db)):
    il = db.get(ImportList, import_list_id)
    if il is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    _validate(body.kind, body.config)
    il.name = body.name
    il.kind = body.kind
    il.config = json.dumps(body.config)
    il.quality_profile_id = body.quality_profile_id
    il.enabled = body.enabled
    db.commit()
    return _out(il)


@router.delete("/{import_list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_import_list(import_list_id: int, db: Session = Depends(get_db)):
    il = db.get(ImportList, import_list_id)
    if il is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(il)
    db.commit()


@router.post("/{import_list_id}/sync")
async def sync_import_list(import_list_id: int, db: Session = Depends(get_db)):
    il = db.get(ImportList, import_list_id)
    if il is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    result = await import_lists_service.sync_one(db, il)
    return _out(il) | {"result": result}
