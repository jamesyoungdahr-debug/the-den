"""First-run setup (M33): until an admin exists and the setup wizard is finished, the server
serves only the setup and sign-in pages, and answers every app or API call with 503."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import auth
from app import settings as settings_module

_complete = False


def is_complete(db: Session) -> bool:
    """Cached once true: setup can't become unfinished again while the process runs (a database
    restore only takes effect at the next startup, which starts with a fresh cache)."""
    global _complete
    if not _complete:
        _complete = auth.users_exist(db) and settings_module.get_row(db).setup_completed_at is not None
    return _complete


def mark_complete(db: Session) -> None:
    global _complete
    settings_module.get_row(db).setup_completed_at = datetime.now(timezone.utc)
    db.commit()
    _complete = True


def open_during_setup(path: str) -> bool:
    """Paths that must keep working before setup is finished: health, static assets, the
    wizard, and signing in (an existing install's admin signs in to finish the wizard)."""
    return (
        path == "/health"
        or path.startswith("/static/")
        or path in ("/setup", "/setup/server", "/login", "/logout", "/favicon.ico")
        or path.startswith("/login/plex")
    )
