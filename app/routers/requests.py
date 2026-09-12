"""Requests (M11f): the queue page and JSON API. Users see and manage their own; admins
see everyone's and approve or decline."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth, requests_service as svc
from app.deps import get_db
from app.models import MediaRequest, User
from app.templating import templates

router = APIRouter(tags=["requests"])
USER = [Depends(auth.page_user)]
ADMIN = [Depends(auth.page_admin)]


def _out(db: Session, req: MediaRequest, users: dict[int, User]) -> dict:
    requester = users.get(req.requested_by)
    decider = users.get(req.decided_by) if req.decided_by else None
    done = svc.fulfilled(db, req)
    return {
        "id": req.id, "media_type": req.media_type, "tmdb_id": req.tmdb_id, "title": req.title, "year": req.year,
        "poster_path": req.poster_path, "seasons": req.season_list, "status": req.status,
        "display_status": "available" if done else req.status, "note": req.note,
        "requested_by": {"id": requester.id, "username": requester.username, "initial": requester.initial} if requester else None,
        "decided_by": decider.username if decider else None,
        "decided_at": req.decided_at.isoformat() if req.decided_at else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "available_at": req.available_at.isoformat() if req.available_at else None,
        "movie_id": req.movie_id, "series_id": req.series_id, "label": svc.label(req),
        "href": f"/discover/{req.media_type}/{req.tmdb_id}",
    }


def _visible(db: Session, request: Request, status: str | None, mine: bool) -> list[MediaRequest]:
    me = getattr(request.state, "user", None)
    q = db.query(MediaRequest)
    if not auth.is_admin(request) or mine:
        if me is None:
            return []
        q = q.filter(MediaRequest.requested_by == me.id)
    if status in ("pending", "approved", "declined", "available"):
        q = q.filter(MediaRequest.status == status)
    return q.order_by(MediaRequest.id.desc()).all()


def _users(db: Session, reqs: list[MediaRequest]) -> dict[int, User]:
    ids = {r.requested_by for r in reqs} | {r.decided_by for r in reqs if r.decided_by}
    return {u.id: u for u in db.query(User).filter(User.id.in_(ids))} if ids else {}


def _require_me(request: Request) -> User:
    me = getattr(request.state, "user", None)
    if me is None:
        raise auth.LoginRequired(str(request.url.path))
    return me


# ---- HTML -------------------------------------------------------------------------

@router.get("/requests", response_class=HTMLResponse, dependencies=USER)
def requests_page(request: Request, status: str = "all", db: Session = Depends(get_db)):
    reqs = _visible(db, request, status if status != "all" else None, mine=False)
    users = _users(db, reqs)
    items = [_out(db, r, users) for r in reqs]
    pending = db.query(MediaRequest).filter(MediaRequest.status == "pending").count() if auth.is_admin(request) else None
    me = getattr(request.state, "user", None)
    quota = svc.quota(db, me) if me is not None and not me.is_admin else None
    return templates.TemplateResponse(
        "requests.html",
        {"request": request, "items": items, "status": status, "pending_total": pending, "quota": quota,
         "notice": request.query_params.get("notice"), "error": request.query_params.get("error"), "active_nav": "requests"},
    )


@router.post("/ui/requests", dependencies=USER)
async def ui_create(
    request: Request, media_type: str = Form(...), tmdb_id: int = Form(...), seasons: list[int] = Form([]),
    db: Session = Depends(get_db),
):
    me = _require_me(request)
    back = f"/discover/{media_type}/{tmdb_id}"
    try:
        req = await svc.create_request(db, db.get(User, me.id), media_type, tmdb_id, seasons)
    except svc.RequestError as exc:
        return RedirectResponse(f"{back}?error={exc.message.replace(' ', '+')}", status_code=303)
    what = "approved and added to the library" if req.status == "approved" else "sent for approval"
    return RedirectResponse(f"{back}?notice=Request+{what.replace(' ', '+')}.", status_code=303)


@router.post("/ui/requests/{req_id}/approve", dependencies=ADMIN)
async def ui_approve(request: Request, req_id: int, db: Session = Depends(get_db)):
    req = db.get(MediaRequest, req_id)
    if req is None:
        raise HTTPException(404, "Request not found")
    me = _require_me(request)
    try:
        await svc.approve(db, req, db.get(User, me.id))
    except svc.RequestError as exc:
        return RedirectResponse(f"/requests?error={exc.message.replace(' ', '+')}", status_code=303)
    return RedirectResponse("/requests?notice=Approved.", status_code=303)


@router.post("/ui/requests/{req_id}/decline", dependencies=ADMIN)
async def ui_decline(request: Request, req_id: int, note: str = Form(""), db: Session = Depends(get_db)):
    req = db.get(MediaRequest, req_id)
    if req is None:
        raise HTTPException(404, "Request not found")
    me = _require_me(request)
    await svc.decline(db, req, db.get(User, me.id), note)
    return RedirectResponse("/requests?notice=Declined.", status_code=303)


@router.post("/ui/requests/{req_id}/delete", dependencies=USER)
def ui_delete(request: Request, req_id: int, db: Session = Depends(get_db)):
    req = db.get(MediaRequest, req_id)
    me = _require_me(request)
    if req is None:
        return RedirectResponse("/requests", status_code=303)
    if not auth.is_admin(request) and (req.requested_by != me.id or req.status != "pending"):
        raise auth.Forbidden()
    db.delete(req)
    db.commit()
    return RedirectResponse("/requests?notice=Request+withdrawn.", status_code=303)


# ---- JSON -------------------------------------------------------------------------

class RequestCreate(BaseModel):
    media_type: str
    tmdb_id: int
    seasons: list[int] | None = None


class DeclineBody(BaseModel):
    note: str | None = None


@router.get("/api/requests", dependencies=[Depends(auth.require_user)])
def api_list(request: Request, status: str | None = None, mine: bool = False, db: Session = Depends(get_db)):
    reqs = _visible(db, request, status, mine)
    users = _users(db, reqs)
    return [_out(db, r, users) for r in reqs]


@router.get("/api/requests/quota", dependencies=[Depends(auth.require_user)])
def api_quota(request: Request, db: Session = Depends(get_db)):
    """The caller's request allowance for the current window (admins: exempt)."""
    me = getattr(request.state, "user", None)
    if me is None:
        return {"exempt": True, "days": None, "movies": None, "series": None}
    return svc.quota(db, db.get(User, me.id))


@router.post("/api/requests", status_code=201, dependencies=[Depends(auth.require_user)])
async def api_create(body: RequestCreate, request: Request, db: Session = Depends(get_db)):
    me = getattr(request.state, "user", None)
    if me is None:
        raise HTTPException(401, "Sign in to request")
    try:
        req = await svc.create_request(db, db.get(User, me.id), body.media_type, body.tmdb_id, body.seasons)
    except svc.RequestError as exc:
        raise HTTPException(exc.status, exc.message)
    return _out(db, req, _users(db, [req]))


@router.post("/api/requests/{req_id}/approve", dependencies=[Depends(auth.require_admin)])
async def api_approve(request: Request, req_id: int, db: Session = Depends(get_db)):
    req = db.get(MediaRequest, req_id)
    if req is None:
        raise HTTPException(404, "Request not found")
    me = getattr(request.state, "user", None)
    if me is None:
        raise HTTPException(401, "Sign in to approve")
    try:
        await svc.approve(db, req, db.get(User, me.id))
    except svc.RequestError as exc:
        raise HTTPException(exc.status, exc.message)
    return _out(db, req, _users(db, [req]))


@router.post("/api/requests/{req_id}/decline", dependencies=[Depends(auth.require_admin)])
async def api_decline(request: Request, req_id: int, body: DeclineBody | None = None, db: Session = Depends(get_db)):
    req = db.get(MediaRequest, req_id)
    if req is None:
        raise HTTPException(404, "Request not found")
    me = getattr(request.state, "user", None)
    if me is None:
        raise HTTPException(401, "Sign in to decline")
    await svc.decline(db, req, db.get(User, me.id), body.note if body else None)
    return _out(db, req, _users(db, [req]))


@router.delete("/api/requests/{req_id}", status_code=204, dependencies=[Depends(auth.require_user)])
def api_delete(request: Request, req_id: int, db: Session = Depends(get_db)):
    req = db.get(MediaRequest, req_id)
    if req is None:
        raise HTTPException(404, "Request not found")
    me = getattr(request.state, "user", None)
    if not auth.is_admin(request) and (me is None or req.requested_by != me.id or req.status != "pending"):
        raise HTTPException(403, "Only your own pending requests can be withdrawn")
    db.delete(req)
    db.commit()
