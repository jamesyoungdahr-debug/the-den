from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import config, scheduler
from app import settings as settings_module
from app.deps import get_db
from app.torrent import engine

router = APIRouter(prefix="/api", tags=["settings"])


class SettingsUpdate(BaseModel):
    """Partial update body. A missing field is left untouched; a present non-secret
    field always takes the submitted value (blank -> use the env-var default)."""

    tmdb_api_key: str | None = None
    movies_root: str | None = None
    tv_root: str | None = None
    # Same minimum as the HTML settings form (app/templates/settings.html's
    # min="60"). Without it, an explicit 0 would be stored and then silently
    # discarded by settings.effective()'s fallback, with no indication to the caller.
    automation_interval_seconds: int | None = Field(default=None, ge=60)
    discord_webhook_url: str | None = None
    # Built-in torrent client. 0 on a limit means "no limit".
    downloads_root: str | None = None
    torrent_port: int | None = Field(default=None, ge=1024, le=65535)
    download_rate_limit_kib: int | None = Field(default=None, ge=0)
    upload_rate_limit_kib: int | None = Field(default=None, ge=0)
    seed_ratio_limit: float | None = Field(default=None, ge=0)
    seed_time_limit_minutes: int | None = Field(default=None, ge=0)


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Effective settings (DB overrides layered on env defaults) as JSON.

    Secret values (TMDB key, Discord webhook) are never echoed back -- the client
    gets a has_* boolean instead so it can show a "currently set" hint without ever
    seeing the stored value.
    """
    s = settings_module.effective(db)
    row = settings_module.get_row(db)
    return {
        "tmdb_api_key": "",
        "has_tmdb_api_key": bool(row.tmdb_api_key),
        "movies_root": s.movies_root,
        "tv_root": s.tv_root,
        "automation_interval_seconds": s.automation_interval_seconds,
        "discord_webhook_url": "",
        "has_discord_webhook": bool(row.discord_webhook_url),
        "downloads_root": s.downloads_root,
        "state_dir": config.STATE_DIR,  # read-only: an install-location fact, not a preference
        "torrent_port": s.torrent_port,
        "download_rate_limit_kib": s.download_rate_limit_kib,
        "upload_rate_limit_kib": s.upload_rate_limit_kib,
        "seed_ratio_limit": s.seed_ratio_limit,
        "seed_time_limit_minutes": s.seed_time_limit_minutes,
    }


def apply_runtime_changes(old: settings_module.EffectiveSettings, new: settings_module.EffectiveSettings) -> None:
    """Push settings that have live effect into the running scheduler/engine. Shared
    with the HTML settings form in app/routers/ui.py."""
    if new.automation_interval_seconds != old.automation_interval_seconds:
        try:
            scheduler.reschedule(new.automation_interval_seconds)
        except Exception:
            # Scheduler only runs in the live app (started on startup); under tests or
            # if it isn't running, the next startup picks up the new interval anyway.
            pass
    if new.engine_config() != old.engine_config():
        engine.apply_config(new.engine_config())


@router.post("/settings")
def save_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    row = settings_module.get_row(db)
    old = settings_module.effective(db)

    # Secret fields: only overwrite when a new non-empty value is supplied.
    if payload.tmdb_api_key:
        row.tmdb_api_key = payload.tmdb_api_key
    if payload.discord_webhook_url:
        row.discord_webhook_url = payload.discord_webhook_url

    # Non-secret fields: always take the submitted value (blank -> use the default).
    if payload.movies_root is not None:
        row.movies_root = payload.movies_root or None
    if payload.tv_root is not None:
        row.tv_root = payload.tv_root or None
    if payload.automation_interval_seconds is not None:
        row.automation_interval_seconds = payload.automation_interval_seconds
    if payload.downloads_root is not None:
        row.downloads_root = payload.downloads_root or None
    for field in ("torrent_port", "download_rate_limit_kib", "upload_rate_limit_kib",
                  "seed_ratio_limit", "seed_time_limit_minutes"):
        value = getattr(payload, field)
        if value is not None:
            setattr(row, field, value)

    db.commit()
    apply_runtime_changes(old, settings_module.effective(db))
    return get_settings(db)
