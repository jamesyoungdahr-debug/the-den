from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth
from app import indexers as indexer_engine
from app.deps import get_db
from app.models import Indexer
from app.schemas import IndexerCreate, IndexerOut

router = APIRouter(prefix="/indexers", tags=["indexers"], dependencies=[Depends(auth.require_admin)])


@router.get("/presets")
def list_presets():
    """The catalog: public trackers, usenet indexers and the generic Torznab/Newznab
    entries. The client picks one, fills in what `fields` asks for, and POSTs /indexers."""
    return indexer_engine.as_dicts()


class SolverTest(BaseModel):
    url: str | None = None


@router.post("/solver/test")
async def test_solver(payload: SolverTest | None = None, db: Session = Depends(get_db)):
    """Check the FlareSolverr/Byparr instance: the URL in the body, or the saved one."""
    from app import settings as settings_module

    url = (payload.url if payload and payload.url else settings_module.effective(db).flaresolverr_url) or ""
    if not url:
        from app.indexers import solver

        st = solver.status()
        if not st["builtin"]:
            raise HTTPException(400, "No external solver URL set and the built-in one needs Chromium on the server (none found)")
        try:
            html = await solver.fetch("https://1337x.to/home/", timeout=60)
        except Exception as exc:
            raise HTTPException(502, f"Built-in solver failed: {exc}")
        return {"ok": True, "solver": "built-in (Chromium)", "chrome": st["chrome"], "version": st["nodriver"], "sample_bytes": len(html)}
    try:
        return await indexer_engine.test_solver(url)
    except Exception as exc:
        raise HTTPException(502, f"Solver test failed: {exc}")


@router.get("", response_model=list[IndexerOut])
def list_indexers(db: Session = Depends(get_db)):
    return db.query(Indexer).all()


@router.post("", response_model=IndexerOut, status_code=201)
def create_indexer(payload: IndexerCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    preset = indexer_engine.BY_SLUG.get(data.get("preset") or "")
    if preset:
        data["implementation"] = data.get("implementation") or preset.implementation
        data["url"] = data.get("url") or preset.url
        data["name"] = data.get("name") or preset.name
    impl = data.get("implementation") or data.get("protocol") or "torznab"
    if impl not in ("torznab", "newznab") and impl not in indexer_engine.NATIVES:
        raise HTTPException(400, f"Unknown indexer implementation '{impl}'")
    data["implementation"] = impl
    data["protocol"] = impl if impl in ("torznab", "newznab") else "native"
    if not data.get("url"):
        raise HTTPException(400, "URL is required")
    if not data.get("name"):
        raise HTTPException(400, "Name is required")
    indexer = Indexer(**data)
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
        return await indexer_engine.test_one(indexer, db)
    except Exception as exc:
        raise HTTPException(502, f"Connection test failed: {exc}")


@router.delete("/{indexer_id}", status_code=204)
def delete_indexer(indexer_id: int, db: Session = Depends(get_db)):
    indexer = db.get(Indexer, indexer_id)
    if not indexer:
        raise HTTPException(404, "Indexer not found")
    db.delete(indexer)
    db.commit()
