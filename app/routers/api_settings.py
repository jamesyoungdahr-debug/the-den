from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import scheduler
from app import settings as settings_module
from app.deps import get_db

router = APIRouter(prefix="/api", tags=["settings"])


class SettingsUpdate(BaseModel):
    """Partial update body. A missing field is left untouched; a present non-secret
    field always takes the submitted value (blank -> use the env-var default)."""

    tmdb_api_key: str | None = None
    qbit_url: str | None = None
    qbit_username: str | None = None
    qbit_password: str | None = None
    movies_root: str | None = None
    tv_root: str | None = None
    automation_interval_seconds: int | None = None
    discord_webhook_url: str | None = None


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Effective settings (DB overrides layered on env defaults) as JSON.

    Secret values (TMDB key, qBittorrent password, Discord webhook) are never echoed
    back -- the client gets a has_* boolean instead so it can show a "currently set"
    hint without ever seeing the stored value.
    """
    s = settings_module.effective(db)
    row = settings_module.get_row(db)
    return {
        "tmdb_api_key": "",
        "has_tmdb_api_key": bool(row.tmdb_api_key),
        "qbit_url": s.qbit_url,
        "qbit_username": s.qbit_username,
        "qbit_password": "",
        "has_qbit_password": bool(row.qbit_password),
        "movies_root": s.movies_root,
        "tv_root": s.tv_root,
        "automation_interval_seconds": s.automation_interval_seconds,
        "discord_webhook_url": "",
        "has_discord_webhook": bool(row.discord_webhook_url),
    }


@router.post("/settings")
def save_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    row = settings_module.get_row(db)
    old_interval = settings_module.effective(db).automation_interval_seconds

    # Secret fields: only overwrite when a new non-empty value is supplied.
    if payload.tmdb_api_key:
        row.tmdb_api_key = payload.tmdb_api_key
    if payload.qbit_password:
        row.qbit_password = payload.qbit_password
    if payload.discord_webhook_url:
        row.discord_webhook_url = payload.discord_webhook_url

    # Non-secret fields: always take the submitted value (blank -> use the default).
    if payload.qbit_url is not None:
        row.qbit_url = payload.qbit_url or None
    if payload.qbit_username is not None:
        row.qbit_username = payload.qbit_username or None
    if payload.movies_root is not None:
        row.movies_root = payload.movies_root or None
    if payload.tv_root is not None:
        row.tv_root = payload.tv_root or None
    if payload.automation_interval_seconds is not None:
        row.automation_interval_seconds = payload.automation_interval_seconds

    db.commit()

    new_interval = settings_module.effective(db).automation_interval_seconds
    if new_interval != old_interval:
        try:
            scheduler.reschedule(new_interval)
        except Exception:
            # Scheduler only runs in the live app (started on startup); under tests or
            # if it isn't running, the next startup picks up the new interval anyway.
            pass

    return get_settings(db)
