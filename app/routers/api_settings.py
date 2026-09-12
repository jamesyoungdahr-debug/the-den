import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import auth
from app import config, scheduler
from app import settings as settings_module
from app.deps import get_db
from app.torrent import engine

router = APIRouter(prefix="/api", tags=["settings"], dependencies=[Depends(auth.require_admin)])


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
    # Plex (the owner token is only ever set through the sign-in flow, never posted here)
    plex_machine_id: str | None = None
    plex_server_name: str | None = None
    plex_url: str | None = None
    plex_sections: list[str] | None = None
    plex_allow_any_account: bool | None = None
    plex_scan_interval_minutes: int | None = Field(default=None, ge=5)
    # Request quotas for non-admins (M11g); 0 = unlimited
    request_movie_limit: int | None = Field(default=None, ge=0)
    request_series_limit: int | None = Field(default=None, ge=0)
    request_limit_days: int | None = Field(default=None, ge=1)
    # Require sign-in everywhere (overrides the AUTH_REQUIRED env var). Only a signed-in
    # admin may turn it on, so nobody locks themselves out.
    auth_required: bool | None = None


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
        "has_plex_token": bool(s.plex_token),
        "plex_owner_username": s.plex_owner_username,
        "plex_server_name": s.plex_server_name,
        "plex_machine_id": s.plex_machine_id,
        "plex_url": s.plex_url,
        "plex_sections": s.plex_sections,
        "plex_allow_any_account": s.plex_allow_any_account,
        "plex_scan_interval_minutes": s.plex_scan_interval_minutes,
        "plex_last_scan_at": row.plex_last_scan_at.isoformat() if row.plex_last_scan_at else None,
        "plex_last_scan_result": row.plex_last_scan_result,
        "request_movie_limit": s.request_movie_limit,
        "request_series_limit": s.request_series_limit,
        "request_limit_days": s.request_limit_days,
        "auth_required": auth.required(),
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
    if new.plex_scan_interval_minutes != old.plex_scan_interval_minutes:
        try:
            scheduler.reschedule_plex(new.plex_scan_interval_minutes)
        except Exception:
            pass


@router.post("/settings")
def save_settings(payload: SettingsUpdate, request: Request, db: Session = Depends(get_db)):
    row = settings_module.get_row(db)
    old = settings_module.effective(db)

    if payload.auth_required is not None:
        if payload.auth_required and getattr(request.state, "user", None) is None:
            raise HTTPException(400, "Sign in as an admin before requiring sign-in, or you'd lock yourself out")
        row.auth_required = payload.auth_required
        auth.set_required_override(payload.auth_required)
    for field in ("request_movie_limit", "request_series_limit", "request_limit_days"):
        value = getattr(payload, field)
        if value is not None:
            setattr(row, field, value)

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
    for field in ("plex_machine_id", "plex_server_name", "plex_url"):
        value = getattr(payload, field)
        if value is not None:
            setattr(row, field, value or None)
    if payload.plex_sections is not None:
        row.plex_sections = json.dumps(payload.plex_sections) if payload.plex_sections else None
    if payload.plex_allow_any_account is not None:
        row.plex_allow_any_account = payload.plex_allow_any_account
    if payload.plex_scan_interval_minutes is not None:
        row.plex_scan_interval_minutes = payload.plex_scan_interval_minutes

    db.commit()
    apply_runtime_changes(old, settings_module.effective(db))
    return get_settings(db)
