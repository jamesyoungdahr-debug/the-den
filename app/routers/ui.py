from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import torznab
from app.deps import get_db
from app.models import Indexer

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
