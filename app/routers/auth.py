"""Sign in / sign out / first-run setup, as HTML pages and as JSON for the companion apps."""

import socket

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth, plex, plex_access, requests_service, setup_state
from app import settings as settings_module
from app.deps import get_db
from app.models import User
from app.routers.api_settings import apply_runtime_changes
from app.templating import templates

router = APIRouter(tags=["auth"])

PLEX_PURPOSES = ("signin", "owner", "link")


def _safe_next(value: str | None) -> str:
    # Only ever redirect within the app.
    return value if value and value.startswith("/") and not value.startswith("//") else "/"


def _user_out(user: User) -> dict:
    return {
        "id": user.id, "username": user.username, "email": user.email, "avatar_url": user.avatar_url,
        "role": user.role, "is_admin": user.is_admin, "auto_approve": user.auto_approve,
        "plex_linked": user.plex_id is not None, "has_api_token": bool(user.api_token),
        "notify_ntfy_topic": user.notify_ntfy_topic,
    }


# ---- first-run setup ----------------------------------------------------------------
# Step 1 creates the admin (password here, or Plex via /login/plex). Step 2 names the server
# and sets the library folders. Until step 2 is saved, app.main serves only these pages.

@router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request, db: Session = Depends(get_db)):
    if setup_state.is_complete(db):
        return RedirectResponse("/", status_code=303)
    if auth.users_exist(db):
        return RedirectResponse("/setup/server", status_code=303)
    return templates.TemplateResponse("setup.html", {"request": request, "error": None})


@router.post("/setup")
def setup_submit(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if auth.users_exist(db):
        return RedirectResponse("/setup", status_code=303)
    username = username.strip()
    if len(username) < 2 or len(password) < 8:
        return templates.TemplateResponse(
            "setup.html", {"request": request, "error": "Pick a username of 2+ characters and a password of 8+."}, status_code=400
        )
    user = User(username=username, password_hash=auth.hash_password(password), role="admin", auto_approve=True)
    db.add(user)
    db.commit()
    auth.sign_in(request, db, user)
    return RedirectResponse("/setup/server", status_code=303)


def _setup_server_page(request: Request, values: dict, error: str | None = None, status: int = 200):
    return templates.TemplateResponse(
        "setup_server.html", {"request": request, "values": values, "hostname": socket.gethostname(), "error": error}, status_code=status
    )


@router.get("/setup/server", response_class=HTMLResponse)
def setup_server_page(request: Request, user: User = Depends(auth.page_admin), db: Session = Depends(get_db)):
    if setup_state.is_complete(db):
        return RedirectResponse("/", status_code=303)
    s = settings_module.effective(db)
    values = {"server_name": s.server_name or "", "movies_root": s.movies_root, "tv_root": s.tv_root, "downloads_root": s.downloads_root}
    return _setup_server_page(request, values)


@router.post("/setup/server")
def setup_server_submit(
    request: Request, server_name: str = Form(""), movies_root: str = Form(""), tv_root: str = Form(""),
    downloads_root: str = Form(""), user: User = Depends(auth.page_admin), db: Session = Depends(get_db),
):
    if setup_state.is_complete(db):
        return RedirectResponse("/", status_code=303)
    values = {"server_name": server_name.strip(), "movies_root": movies_root.strip(), "tv_root": tv_root.strip(), "downloads_root": downloads_root.strip()}
    if not (values["movies_root"] and values["tv_root"] and values["downloads_root"]):
        return _setup_server_page(request, values, "All three folders are needed.", status=400)
    old = settings_module.effective(db)
    row = settings_module.get_row(db)
    row.server_name = values["server_name"] or None
    row.movies_root = values["movies_root"]
    row.tv_root = values["tv_root"]
    row.downloads_root = values["downloads_root"]
    setup_state.mark_complete(db)
    new = settings_module.effective(db)
    apply_runtime_changes(old, new)
    from app import discovery

    discovery.start_from_thread(new)  # the server stayed off the LAN until setup was finished
    return RedirectResponse("/", status_code=303)


# ---- sign in / out ------------------------------------------------------------------

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


# ---- Plex sign-in (PIN flow) -------------------------------------------------------

def _login_error(request: Request, db: Session, message: str, next_url: str = "/", status: int = 400):
    if not auth.users_exist(db):
        return templates.TemplateResponse("setup.html", {"request": request, "error": message}, status_code=status)
    return templates.TemplateResponse("login.html", {"request": request, "error": message, "next": next_url}, status_code=status)


@router.get("/login/plex")
async def login_plex_start(request: Request, next: str | None = None, purpose: str = "signin", db: Session = Depends(get_db)):
    """Create a PIN, remember it in the session, and send the browser to plex.tv.
    purpose: signin (default) | owner (an admin connecting the server account from
    Settings) | link (attach Plex to the signed-in local account from Profile)."""
    if purpose not in PLEX_PURPOSES:
        purpose = "signin"
    me = getattr(request.state, "user", None)
    if purpose == "owner" and not auth.is_admin(request):
        raise auth.Forbidden()
    if purpose == "link" and me is None:
        raise auth.LoginRequired("/ui/profile")
    try:
        pin = await plex.create_pin()
    except Exception as exc:
        return _login_error(request, db, f"Couldn't reach plex.tv: {exc}", _safe_next(next), status=502)
    request.session["plex_pin"] = {"id": pin.id, "code": pin.code, "purpose": purpose, "next": _safe_next(next)}
    forward = str(request.url_for("login_plex_callback"))
    return RedirectResponse(plex.auth_url(pin.code, forward), status_code=303)


@router.get("/login/plex/callback")
async def login_plex_callback(request: Request, db: Session = Depends(get_db)):
    pending = request.session.pop("plex_pin", None)
    if not pending:
        return _login_error(request, db, "That Plex sign-in has expired. Try again.")
    next_url, purpose = pending.get("next", "/"), pending.get("purpose", "signin")
    try:
        token = await plex.check_pin(pending["id"], pending["code"])
        if not token:
            return _login_error(request, db, "Plex sign-in wasn't completed. Try again.", next_url, status=401)
        account = await plex.get_account(token)
    except Exception as exc:
        return _login_error(request, db, f"Plex sign-in failed: {exc}", next_url, status=502)

    me = getattr(request.state, "user", None)
    if purpose == "owner":
        if not auth.is_admin(request):
            raise auth.Forbidden()
        plex_access.store_owner(db, account, token)
        if me.plex_id is None:
            plex_access.link_account(db, db.get(User, me.id), account)
        return RedirectResponse("/ui/settings?saved=1#plex", status_code=303)
    if purpose == "link":
        if me is None:
            raise auth.LoginRequired("/ui/profile")
        error = plex_access.link_account(db, db.get(User, me.id), account)
        target = "/ui/profile" + (f"?error={error}" if error else "?notice=Plex+account+linked")
        return RedirectResponse(target, status_code=303)

    user, error = await plex_access.user_for_account(db, account, token)
    if user is None:
        return _login_error(request, db, error or "Sign-in refused.", next_url, status=403)
    auth.sign_in(request, db, user)
    return RedirectResponse(next_url, status_code=303)


class PlexPinBody(BaseModel):
    pin_id: int | None = None
    code: str | None = None
    auth_token: str | None = None


@router.post("/api/auth/plex/pin")
async def api_plex_pin():
    """Step 1 for a native client: a PIN and the plex.tv URL to open in the system browser
    (no forwardUrl -- the client polls step 2 instead)."""
    pin = await plex.create_pin()
    return {"pin_id": pin.id, "code": pin.code, "auth_url": plex.auth_url(pin.code, None), "client_id": plex.client_identifier()}


@router.post("/api/auth/plex")
async def api_plex_login(body: PlexPinBody, request: Request, db: Session = Depends(get_db)):
    """Step 2: exchange the PIN (or a token the client already holds) for a Den session.
    Returns 202 while the PIN hasn't been claimed yet, so clients can poll."""
    token = body.auth_token
    if not token:
        if body.pin_id is None or not body.code:
            raise HTTPException(400, "pin_id and code, or auth_token, are required")
        token = await plex.check_pin(body.pin_id, body.code)
        if not token:
            raise HTTPException(202, "Not signed in on plex.tv yet")
    try:
        account = await plex.get_account(token)
    except plex.PlexError as exc:
        raise HTTPException(401, str(exc))
    user, error = await plex_access.user_for_account(db, account, token)
    if user is None:
        raise HTTPException(403, error or "Sign-in refused")
    auth.sign_in(request, db, user)
    return _user_out(user)


# ---- profile ------------------------------------------------------------------------

@router.get("/ui/profile", response_class=HTMLResponse)
def profile_page(request: Request, user: User = Depends(auth.page_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "user": user, "new_token": None, "quota": requests_service.quota(db, user),
         "error": request.query_params.get("error"), "notice": request.query_params.get("notice")},
    )


@router.post("/ui/profile/token", response_class=HTMLResponse)
def profile_new_token(request: Request, user: User = Depends(auth.page_user), db: Session = Depends(get_db)):
    user = db.get(User, user.id)
    token = auth.new_api_token()
    user.api_token = token
    db.commit()
    # Shown exactly once; only its existence is stored/served afterwards.
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "new_token": token, "quota": requests_service.quota(db, user)})


@router.post("/ui/profile/password")
def profile_change_password(
    request: Request, current_password: str = Form(""), new_password: str = Form(...),
    user: User = Depends(auth.page_user), db: Session = Depends(get_db),
):
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


@router.post("/ui/profile/notifications")
def profile_notifications(
    request: Request, notify_ntfy_topic: str = Form(""),
    user: User = Depends(auth.page_user), db: Session = Depends(get_db),
):
    user = db.get(User, user.id)
    user.notify_ntfy_topic = notify_ntfy_topic.strip() or None
    db.commit()
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "new_token": None, "notice": "Notification settings saved.", "quota": requests_service.quota(db, user)})


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
def api_me(user: User = Depends(auth.require_user), db: Session = Depends(get_db)):
    """Who the caller is, with their request quota."""
    return {**_user_out(user), "quota": requests_service.quota(db, user)}


@router.post("/api/auth/token")
def api_new_token(user: User = Depends(auth.require_user), db: Session = Depends(get_db)):
    """Regenerate the caller's API token. The token is returned once, here only."""
    user = db.get(User, user.id)
    user.api_token = auth.new_api_token()
    db.commit()
    return {"api_token": user.api_token}


class NotificationSettingsBody(BaseModel):
    notify_ntfy_topic: str | None = None


@router.post("/api/auth/notifications")
def api_notification_settings(body: NotificationSettingsBody, user: User = Depends(auth.require_user), db: Session = Depends(get_db)):
    """A personal ntfy.sh topic for this user's own request outcomes (E9)."""
    user = db.get(User, user.id)
    user.notify_ntfy_topic = (body.notify_ntfy_topic or "").strip() or None
    db.commit()
    return _user_out(user)
