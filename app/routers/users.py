"""Admin user management: an HTML page and a JSON API, both admin-only."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth
from app.deps import get_db
from app.models import User
from app.templating import templates

router = APIRouter(tags=["users"])

ROLES = ("admin", "user")


def _out(u: User) -> dict:
    return {
        "id": u.id, "username": u.username, "email": u.email, "role": u.role, "auto_approve": u.auto_approve,
        "movie_limit": u.movie_limit, "series_limit": u.series_limit, "limit_days": u.limit_days,
        "plex_linked": u.plex_id is not None, "has_api_token": bool(u.api_token),
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


# ---- HTML -------------------------------------------------------------------------

@router.get("/ui/users", response_class=HTMLResponse)
def users_page(request: Request, _: User | None = Depends(auth.page_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return templates.TemplateResponse("users.html", {"request": request, "users": users, "error": request.query_params.get("error")})


@router.post("/ui/users")
def ui_create_user(
    username: str = Form(...), password: str = Form(...), role: str = Form("user"),
    auto_approve: str = Form(""), _: User | None = Depends(auth.page_admin), db: Session = Depends(get_db),
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
def ui_set_role(user_id: int, role: str = Form(...), _: User | None = Depends(auth.page_admin), db: Session = Depends(get_db)):
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
def ui_set_auto_approve(user_id: int, enabled: str = Form(""), _: User | None = Depends(auth.page_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    user.auto_approve = enabled == "1"
    db.commit()
    return RedirectResponse("/ui/users", status_code=303)


@router.post("/ui/users/{user_id}/password")
def ui_reset_password(user_id: int, password: str = Form(...), _: User | None = Depends(auth.page_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if len(password) < 8:
        return RedirectResponse("/ui/users?error=Password+needs+8%2B+characters.", status_code=303)
    user.password_hash = auth.hash_password(password)
    db.commit()
    return RedirectResponse("/ui/users", status_code=303)


@router.post("/ui/users/{user_id}/delete")
def ui_delete_user(request: Request, user_id: int, _: User | None = Depends(auth.page_admin), db: Session = Depends(get_db)):
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
    db.delete(user)
    db.commit()
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
def api_list_users(_: User | None = Depends(auth.require_admin), db: Session = Depends(get_db)):
    return [_out(u) for u in db.query(User).order_by(User.id)]


@router.post("/api/users", status_code=201)
def api_create_user(body: UserCreate, _: User | None = Depends(auth.require_admin), db: Session = Depends(get_db)):
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
    return _out(user)


@router.patch("/api/users/{user_id}")
def api_update_user(user_id: int, body: UserUpdate, _: User | None = Depends(auth.require_admin), db: Session = Depends(get_db)):
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
    return _out(user)


@router.delete("/api/users/{user_id}", status_code=204)
def api_delete_user(request: Request, user_id: int, _: User | None = Depends(auth.require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    me = getattr(request.state, "user", None)
    if me is not None and me.id == user.id:
        raise HTTPException(400, "You can't delete yourself")
    _last_admin_guard(db, user, deleting=True)
    db.delete(user)
    db.commit()
