"""Accounts: password hashing, who-is-this resolution, and the guards routes depend on.

Two audiences, two failure modes:
  * JSON API routes use require_user / require_admin, which raise 401 / 403.
  * HTML pages use page_user / page_admin, which raise LoginRequired / Forbidden; app.main
    turns those into a redirect to /login (or /setup on a fresh install) and a 403 page.

AUTH_REQUIRED=false (the env default) means an anonymous visitor is treated as an admin,
so nothing that worked before accounts stops working. Anyone who does sign in is still
tracked by their real role. Settings -> Accounts can override the env flag (M11g); the
override is loaded at startup and whenever it is saved, see required().
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app import config
from app.models import User

SESSION_COOKIE = "den_session"
SESSION_MAX_AGE = 30 * 24 * 3600
API_KEY_HEADER = "x-api-key"

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1

# Settings-level override of config.AUTH_REQUIRED (None = follow the env var).
_required_override: bool | None = None


def required() -> bool:
    """Is sign-in required right now? The Settings override wins over the env var."""
    return config.AUTH_REQUIRED if _required_override is None else _required_override


def set_required_override(value: bool | None) -> None:
    global _required_override
    _required_override = value


class LoginRequired(Exception):
    def __init__(self, next_url: str = "/"):
        self.next_url = next_url


class Forbidden(Exception):
    pass


# ---- passwords ------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        algo, n, r, p, salt_hex, digest_hex = stored.split("$")
        if algo != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def new_api_token() -> str:
    return "den_" + secrets.token_urlsafe(32)


# ---- session secret -------------------------------------------------------------

def session_secret() -> str:
    """SESSION_SECRET from the environment, else one generated once under STATE_DIR."""
    if config.SESSION_SECRET:
        return config.SESSION_SECRET
    path = Path(config.STATE_DIR) / "session_secret"
    try:
        return path.read_text(encoding="utf-8").strip() or _write_secret(path)
    except FileNotFoundError:
        return _write_secret(path)


def _write_secret(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_urlsafe(48)
    path.write_text(secret, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return secret


# ---- who is this? ---------------------------------------------------------------

def users_exist(db: Session) -> bool:
    return db.query(User.id).first() is not None


def resolve_user(request: Request, db: Session) -> User | None:
    """The signed-in user for this request: an X-Api-Key header wins, else the session."""
    token = request.headers.get(API_KEY_HEADER)
    if token:
        return db.query(User).filter(User.api_token == token).first()
    user_id = request.session.get("user_id") if "session" in request.scope else None
    if user_id:
        return db.get(User, user_id)
    return None


def sign_in(request: Request, db: Session, user: User) -> None:
    request.session["user_id"] = user.id
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()


def sign_out(request: Request) -> None:
    request.session.pop("user_id", None)


def _state_user(request: Request) -> User | None:
    return getattr(request.state, "user", None)


def is_admin(request: Request) -> bool:
    user = _state_user(request)
    if user is not None:
        return user.is_admin
    return not required()  # anonymous is admin only while auth is optional


# ---- guards: JSON API ------------------------------------------------------------

def require_user(request: Request) -> User | None:
    user = _state_user(request)
    if user is not None or not required():
        return user
    raise HTTPException(401, "Sign in required")


def require_admin(request: Request) -> User | None:
    user = _state_user(request)
    if user is not None:
        if user.is_admin:
            return user
        raise HTTPException(403, "Admin only")
    if not required():
        return None
    raise HTTPException(401, "Sign in required")


# ---- guards: HTML pages ----------------------------------------------------------

def page_user(request: Request) -> User | None:
    user = _state_user(request)
    if user is not None or not required():
        return user
    raise LoginRequired(str(request.url.path))


def page_admin(request: Request) -> User | None:
    user = _state_user(request)
    if user is not None:
        if user.is_admin:
            return user
        raise Forbidden()
    if not required():
        return None
    raise LoginRequired(str(request.url.path))
