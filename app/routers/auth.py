"""Sign in / sign out / first-run setup, as HTML pages and as JSON for the companion apps."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth
from app.deps import get_db
from app.models import User
from app.templating import templates

router = APIRouter(tags=["auth"])


def _safe_next(value: str | None) -> str:
    # Only ever redirect within the app.
    return value if value and value.startswith("/") and not value.startswith("//") else "/"


def _user_out(user: User) -> dict:
    return {
        "id": user.id, "username": user.username, "email": user.email, "avatar_url": user.avatar_url,
        "role": user.role, "is_admin": user.is_admin, "auto_approve": user.auto_approve,
        "plex_linked": user.plex_id is not None, "has_api_token": bool(user.api_token),
    }


# ---- HTML -------------------------------------------------------------------------

@router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request, db: Session = Depends(get_db)):
    if auth.users_exist(db):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("setup.html", {"request": request, "error": None})


@router.post("/setup")
def setup_submit(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if auth.users_exist(db):
        return RedirectResponse("/login", status_code=303)
    username = username.strip()
    if len(username) < 2 or len(password) < 8:
        return templates.TemplateResponse(
            "setup.html", {"request": request, "error": "Pick a username of 2+ characters and a password of 8+."}, status_code=400
        )
    user = User(username=username, password_hash=auth.hash_password(password), role="admin", auto_approve=True)
    db.add(user)
    db.commit()
    auth.sign_in(request, db, user)
    return RedirectResponse("/", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str | None = None, db: Session = Depends(get_db)):
    if not auth.users_exist(db):
        return RedirectResponse("/setup", status_code=303)
    if getattr(request.state, "user", None) is not None:
        return RedirectResponse(_safe_next(next), status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "next": _safe_next(next)})


@router.post("/login")
def login_submit(
    request: Request, username: str = Form(...), password: str = Form(...), next: str = Form("/"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username.strip()).first()
    if user is None or not auth.verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "That username and password don't match.", "next": _safe_next(next)},
            status_code=401,
        )
    auth.sign_in(request, db, user)
    return RedirectResponse(_safe_next(next), status_code=303)


@router.post("/logout")
def logout(request: Request):
    auth.sign_out(request)
    return RedirectResponse("/login", status_code=303)


@router.get("/ui/profile", response_class=HTMLResponse)
def profile_page(request: Request, user: User | None = Depends(auth.page_user)):
    if user is None:
        raise auth.LoginRequired("/ui/profile")
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "new_token": None})


@router.post("/ui/profile/token", response_class=HTMLResponse)
def profile_new_token(request: Request, user: User | None = Depends(auth.page_user), db: Session = Depends(get_db)):
    if user is None:
        raise auth.LoginRequired("/ui/profile")
    user = db.get(User, user.id)
    token = auth.new_api_token()
    user.api_token = token
    db.commit()
    # Shown exactly once; only its existence is stored/served afterwards.
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "new_token": token})


@router.post("/ui/profile/password")
def profile_change_password(
    request: Request, current_password: str = Form(""), new_password: str = Form(...),
    user: User | None = Depends(auth.page_user), db: Session = Depends(get_db),
):
    if user is None:
        raise auth.LoginRequired("/ui/profile")
    user = db.get(User, user.id)
    if user.password_hash and not auth.verify_password(current_password, user.password_hash):
        return templates.TemplateResponse(
            "profile.html", {"request": request, "user": user, "new_token": None, "error": "Current password is wrong."}, status_code=400
        )
    if len(new_password) < 8:
        return templates.TemplateResponse(
            "profile.html", {"request": request, "user": user, "new_token": None, "error": "New password needs 8+ characters."}, status_code=400
        )
    user.password_hash = auth.hash_password(new_password)
    db.commit()
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "new_token": None, "notice": "Password changed."})


# ---- JSON -------------------------------------------------------------------------

class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/api/auth/login")
def api_login(body: LoginBody, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username.strip()).first()
    if user is None or not auth.verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    auth.sign_in(request, db, user)
    return _user_out(user)


@router.post("/api/auth/logout", status_code=204)
def api_logout(request: Request):
    auth.sign_out(request)


@router.get("/api/auth/me")
def api_me(request: Request):
    """Who the caller is. Anonymous while AUTH_REQUIRED is off is reported as an admin
    with no account, so clients can gate their UI the same way the web UI does."""
    user = getattr(request.state, "user", None)
    if user is None:
        if auth.is_admin(request):
            return {"id": None, "username": None, "role": "admin", "is_admin": True, "anonymous": True, "auth_required": False}
        raise HTTPException(401, "Sign in required")
    return {**_user_out(user), "anonymous": False, "auth_required": True}


@router.post("/api/auth/token")
def api_new_token(request: Request, user: User | None = Depends(auth.require_user), db: Session = Depends(get_db)):
    """Regenerate the caller's API token. The token is returned once, here only."""
    if user is None:
        raise HTTPException(401, "Sign in required")
    user = db.get(User, user.id)
    user.api_token = auth.new_api_token()
    db.commit()
    return {"api_token": user.api_token}
