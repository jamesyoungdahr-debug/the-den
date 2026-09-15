"""Admin user management: an HTML page and a JSON API, both admin-only."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth, device_tokens, playback, sign_in_links
from app import settings as settings_module
from app.deps import get_db
from app.models import User
from app.templating import templates

router = APIRouter(tags=["users"])

ROLES = ("admin", "user")


def _out(db: Session, u: User) -> dict:
    return {
        "id": u.id, "username": u.username, "email": u.email, "role": u.role, "auto_approve": u.auto_approve,
        "movie_limit": u.movie_limit, "series_limit": u.series_limit, "limit_days": u.limit_days,
        "plex_linked": u.plex_id is not None, "device_count": device_tokens.count_for(db, u.id),
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
    }


def _last_admin_guard(db: Session, target: User, new_role: str | None = None, deleting: bool = False) -> None:
    """Never leave the app without an admin."""
    if not target.is_admin:
        return
    if deleting or (new_role and new_role != "admin"):
        others = db.query(User).filter(User.role == "admin", User.id != target.id).count()
        if others == 0:
            raise HTTPException(400, "That's the only admin; promote someone else first.")


def _delete_user(db: Session, user: User) -> None:
    """SQLite doesn't cascade, so the user's device tokens go first; a reused id must never
    inherit someone else's signed-in devices."""
    device_tokens.revoke_all(db, user.id)
    playback.forget_user(db, user.id)
    db.delete(user)
    db.commit()


# ---- HTML -------------------------------------------------------------------------

def _render_users(request: Request, db: Session, new_link: dict | None = None) -> Response:
    """The users page. `new_link` carries a freshly minted sign-in link to show exactly once."""
    users = db.query(User).order_by(User.id).all()
    s = settings_module.effective(db)
    defaults = {"movies": s.request_movie_limit, "series": s.request_series_limit, "days": s.request_limit_days}
    device_counts = {u.id: device_tokens.count_for(db, u.id) for u in users}
    return templates.TemplateResponse(
        "users.html",
        {"request": request, "users": users, "defaults": defaults, "device_counts": device_counts,
         "error": request.query_params.get("error"), "new_link": new_link, "active_nav": "users"},
    )


def _plex_only(db: Session) -> list[User]:
    """Accounts that can still ONLY sign in through Plex.

    An account is Plex-only when it is tied to a Plex id and has never been given a password of
    its own. Plex sign-in keeps working during the parallel period, so these are not broken --
    they are the people who would be locked out the day Plex is switched off."""
    return (
        db.query(User)
        .filter(User.plex_id.isnot(None), User.password_hash.is_(None))
        .order_by(User.username)
        .all()
    )


def _render_migration(request: Request, db: Session, new_link: dict | None = None) -> Response:
    """The migration view. `new_link` carries a freshly minted sign-in link to show exactly once."""
    return templates.TemplateResponse(
        "users_migration.html",
        {"request": request, "plex_only": _plex_only(db), "total": db.query(User).count(),
         "error": request.query_params.get("error"), "new_link": new_link, "active_nav": "users"},
    )


@router.get("/ui/users", response_class=HTMLResponse)
def users_page(request: Request, _: User = Depends(auth.page_admin), db: Session = Depends(get_db)):
    return _render_users(request, db)


@router.get("/ui/users/plex-migration", response_class=HTMLResponse)
def users_plex_migration(request: Request, _: User = Depends(auth.page_admin), db: Session = Depends(get_db)):
    """M51: who can still only sign in with Plex.

    M60's switch-off gate is 'zero Plex-only users' and until this page existed that gate could
    only be guessed at. This is also the shortest path to fixing them: the sign-in link button
    here mints a set-password link without leaving the page."""
    return _render_migration(request, db)


@router.post("/ui/users/{user_id}/sign-in-link")
def ui_create_sign_in_link(request: Request, user_id: int, back: str = Form("users"), _: User = Depends(auth.page_admin), db: Session = Depends(get_db)):
    """M51: mint a one-time link so this person can set their own password.

    Rendered rather than redirected, so the token never reaches a URL bar, browser history or a
    server access log -- this response is the only place it is ever readable. Minting a second
    link quietly retires the first, which is what an admin wants for one that has gone astray.

    `back` says which page asked, so the link is shown on the page the admin was already on."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    token = sign_in_links.create(db, target)
    link = {"username": target.username, "url": f"/join/{token}", "days": sign_in_links.LINK_DAYS}
    if back == "migration":
        return _render_migration(request, db, new_link=link)
    return _render_users(request, db, new_link=link)


@router.post("/ui/users")
def ui_create_user(
    username: str = Form(...), password: str = Form(...), role: str = Form("user"),
    auto_approve: str = Form(""), _: User = Depends(auth.page_admin), db: Session = Depends(get_db),
):
    username = username.strip()
    if len(username) < 2 or len(password) < 8 or role not in ROLES:
        return RedirectResponse("/ui/users?error=Username+needs+2%2B+characters+and+password+8%2B.", status_code=303)
    db.add(User(username=username, password_hash=auth.hash_password(password), role=role, auto_approve=bool(auto_approve)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse("/ui/users?error=That+username+is+taken.", status_code=303)
    return RedirectResponse("/ui/users", status_code=303)


@router.post("/ui/users/{user_id}/role")
def ui_set_role(user_id: int, role: str = Form(...), _: User = Depends(auth.page_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None or role not in ROLES:
        raise HTTPException(404, "User not found")
    try:
        _last_admin_guard(db, user, new_role=role)
    except HTTPException as exc:
        return RedirectResponse(f"/ui/users?error={exc.detail.replace(' ', '+')}", status_code=303)
    user.role = role
    db.commit()
    return RedirectResponse("/ui/users", status_code=303)


@router.post("/ui/users/{user_id}/auto-approve")
def ui_set_auto_approve(user_id: int, enabled: str = Form(""), _: User = Depends(auth.page_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    user.auto_approve = enabled == "1"
    db.commit()
    return RedirectResponse("/ui/users", status_code=303)


@router.post("/ui/users/{user_id}/limits")
def ui_set_limits(
    user_id: int, email: str = Form(""), movie_limit: str = Form(""), series_limit: str = Form(""), limit_days: str = Form(""),
    _: User = Depends(auth.page_admin), db: Session = Depends(get_db),
):
    """Per-user request quota; blank fields fall back to the Settings defaults."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    user.email = email.strip() or None
    user.movie_limit = int(movie_limit) if movie_limit.strip().isdigit() else None
    user.series_limit = int(series_limit) if series_limit.strip().isdigit() else None
    user.limit_days = int(limit_days) if limit_days.strip().isdigit() and int(limit_days) > 0 else None
    db.commit()
    return RedirectResponse("/ui/users", status_code=303)


@router.post("/ui/users/{user_id}/password")
def ui_reset_password(user_id: int, password: str = Form(...), _: User = Depends(auth.page_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if len(password) < 8:
        return RedirectResponse("/ui/users?error=Password+needs+8%2B+characters.", status_code=303)
    user.password_hash = auth.hash_password(password)
    db.commit()
    return RedirectResponse("/ui/users", status_code=303)


@router.post("/ui/users/{user_id}/devices/revoke")
def ui_revoke_devices(user_id: int, _: User = Depends(auth.page_admin), db: Session = Depends(get_db)):
    """Sign every app of this user out."""
    if db.get(User, user_id) is None:
        raise HTTPException(404, "User not found")
    device_tokens.revoke_all(db, user_id)
    return RedirectResponse("/ui/users", status_code=303)


@router.post("/ui/users/{user_id}/delete")
def ui_delete_user(request: Request, user_id: int, _: User = Depends(auth.page_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        return RedirectResponse("/ui/users", status_code=303)
    me = getattr(request.state, "user", None)
    if me is not None and me.id == user.id:
        return RedirectResponse("/ui/users?error=You+can%27t+delete+yourself.", status_code=303)
    try:
        _last_admin_guard(db, user, deleting=True)
    except HTTPException as exc:
        return RedirectResponse(f"/ui/users?error={exc.detail.replace(' ', '+')}", status_code=303)
    _delete_user(db, user)
    return RedirectResponse("/ui/users", status_code=303)


# ---- JSON -------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(min_length=2)
    password: str = Field(min_length=8)
    email: str | None = None
    role: str = "user"
    auto_approve: bool = False


class UserUpdate(BaseModel):
    email: str | None = None
    role: str | None = None
    auto_approve: bool | None = None
    movie_limit: int | None = Field(default=None, ge=0)
    series_limit: int | None = Field(default=None, ge=0)
    limit_days: int | None = Field(default=None, ge=1)
    password: str | None = Field(default=None, min_length=8)


@router.get("/api/users")
def api_list_users(_: User = Depends(auth.require_admin), db: Session = Depends(get_db)):
    return [_out(db, u) for u in db.query(User).order_by(User.id)]


@router.post("/api/users", status_code=201)
def api_create_user(body: UserCreate, _: User = Depends(auth.require_admin), db: Session = Depends(get_db)):
    if body.role not in ROLES:
        raise HTTPException(400, "role must be admin or user")
    user = User(
        username=body.username.strip(), email=body.email, password_hash=auth.hash_password(body.password),
        role=body.role, auto_approve=body.auto_approve,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "That username is taken")
    return _out(db, user)


@router.patch("/api/users/{user_id}")
def api_update_user(user_id: int, body: UserUpdate, _: User = Depends(auth.require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if body.role is not None:
        if body.role not in ROLES:
            raise HTTPException(400, "role must be admin or user")
        _last_admin_guard(db, user, new_role=body.role)
        user.role = body.role
    for field in ("email", "auto_approve", "movie_limit", "series_limit", "limit_days"):
        value = getattr(body, field)
        if value is not None:
            setattr(user, field, value)
    if body.password:
        user.password_hash = auth.hash_password(body.password)
    db.commit()
    return _out(db, user)


@router.delete("/api/users/{user_id}/devices")
def api_revoke_devices(user_id: int, _: User = Depends(auth.require_admin), db: Session = Depends(get_db)):
    """Sign every app of this user out."""
    if db.get(User, user_id) is None:
        raise HTTPException(404, "User not found")
    return {"revoked": device_tokens.revoke_all(db, user_id)}


@router.delete("/api/users/{user_id}", status_code=204)
def api_delete_user(request: Request, user_id: int, _: User = Depends(auth.require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    me = getattr(request.state, "user", None)
    if me is not None and me.id == user.id:
        raise HTTPException(400, "You can't delete yourself")
    _last_admin_guard(db, user, deleting=True)
    _delete_user(db, user)
