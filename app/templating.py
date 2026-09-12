"""The one Jinja environment every HTML router shares: filters, globals, and the request
context every page gets (who is signed in, whether they're an admin)."""

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app import auth

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w342"


def poster_url(path: str | None) -> str:
    """TMDB stores a bare path ('/abc.jpg'); TVmaze stores a full URL. Either way, a URL."""
    if not path:
        return ""
    if path.startswith("http") or path.startswith("/api/"):  # full URL, or our own Plex thumb proxy
        return path
    return f"{TMDB_IMAGE_BASE}{path}"


def _static_version() -> str:
    """Cache-buster for the stylesheet/script links: the newest mtime among the static
    assets, so a deploy (or a dev restart) makes every browser fetch fresh copies."""
    static_dir = Path(__file__).resolve().parent / "static"
    try:
        return str(int(max(p.stat().st_mtime for p in static_dir.iterdir() if p.is_file())))
    except (OSError, ValueError):
        return "0"


def _pending_requests(request: Request) -> int:
    """Badge count for the sidebar: pending requests, admins only. One COUNT per page."""
    if not auth.is_admin(request):
        return 0
    from app.db import SessionLocal
    from app.models import MediaRequest

    db = SessionLocal()
    try:
        return db.query(MediaRequest).filter(MediaRequest.status == "pending").count()
    except Exception:
        return 0
    finally:
        db.close()


def _request_context(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    return {
        "current_user": user,
        "is_admin": auth.is_admin(request),
        "auth_required": auth.required(),
        "pending_requests": _pending_requests(request),
    }


templates = Jinja2Templates(directory="app/templates", context_processors=[_request_context])
templates.env.filters["poster"] = poster_url
templates.env.globals["static_v"] = _static_version()
