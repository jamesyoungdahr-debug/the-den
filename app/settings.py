import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app import config
from app.models import Settings
from app.torrent import EngineConfig

SETTINGS_ROW_ID = 1


@dataclass
class EffectiveSettings:
    tmdb_api_key: str
    movies_root: str
    tv_root: str
    automation_interval_seconds: int
    discord_webhook_url: str
    downloads_root: str
    torrent_port: int
    download_rate_limit_kib: int
    upload_rate_limit_kib: int
    seed_ratio_limit: float
    seed_time_limit_minutes: int
    plex_token: str
    plex_owner_id: int | None
    plex_owner_username: str | None
    plex_server_name: str | None
    plex_machine_id: str | None
    plex_url: str
    plex_sections: list[str]
    plex_allow_any_account: bool
    plex_scan_interval_minutes: int
    import_list_interval_minutes: int
    opensubtitles_api_key: str
    subtitle_languages: list[str]
    request_movie_limit: int
    request_series_limit: int
    request_limit_days: int
    auth_required: bool
    flaresolverr_url: str

    def engine_config(self) -> EngineConfig:
        return EngineConfig(
            state_dir=config.STATE_DIR,
            downloads_root=self.downloads_root,
            listen_port=self.torrent_port,
            download_rate_limit_kib=self.download_rate_limit_kib,
            upload_rate_limit_kib=self.upload_rate_limit_kib,
            seed_ratio_limit=self.seed_ratio_limit,
            seed_time_limit_minutes=self.seed_time_limit_minutes,
        )


def get_row(db: Session) -> Settings:
    row = db.get(Settings, SETTINGS_ROW_ID)
    if not row:
        row = Settings(id=SETTINGS_ROW_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _pick(stored, default):
    """A stored null (or blank string) means "use the default". A stored 0 is a real
    value -- for the rate/seed limits it means "unlimited" -- so this is deliberately
    not `stored or default`."""
    if stored is None or stored == "":
        return default
    return stored


def effective(db: Session) -> EffectiveSettings:
    """DB overrides layered on top of app/config.py's env-var defaults."""
    row = get_row(db)
    return EffectiveSettings(
        tmdb_api_key=_pick(row.tmdb_api_key, config.TMDB_API_KEY),
        movies_root=_pick(row.movies_root, config.MOVIES_ROOT),
        tv_root=_pick(row.tv_root, config.TV_ROOT),
        automation_interval_seconds=_pick(row.automation_interval_seconds, config.AUTOMATION_INTERVAL_SECONDS),
        discord_webhook_url=_pick(row.discord_webhook_url, config.DISCORD_WEBHOOK_URL),
        downloads_root=_pick(row.downloads_root, config.DOWNLOADS_ROOT),
        torrent_port=_pick(row.torrent_port, config.TORRENT_PORT),
        download_rate_limit_kib=_pick(row.download_rate_limit_kib, config.DOWNLOAD_RATE_LIMIT_KIB),
        upload_rate_limit_kib=_pick(row.upload_rate_limit_kib, config.UPLOAD_RATE_LIMIT_KIB),
        seed_ratio_limit=_pick(row.seed_ratio_limit, config.SEED_RATIO_LIMIT),
        seed_time_limit_minutes=_pick(row.seed_time_limit_minutes, config.SEED_TIME_LIMIT_MINUTES),
        plex_token=_pick(row.plex_token, config.PLEX_TOKEN),
        plex_owner_id=row.plex_owner_id,
        plex_owner_username=row.plex_owner_username,
        plex_server_name=row.plex_server_name,
        plex_machine_id=row.plex_machine_id,
        plex_url=_pick(row.plex_url, config.PLEX_URL),
        plex_sections=json.loads(row.plex_sections) if row.plex_sections else [],
        plex_allow_any_account=bool(row.plex_allow_any_account),
        plex_scan_interval_minutes=_pick(row.plex_scan_interval_minutes, config.PLEX_SCAN_INTERVAL_MINUTES),
        import_list_interval_minutes=_pick(row.import_list_interval_minutes, config.IMPORT_LIST_INTERVAL_MINUTES),
        opensubtitles_api_key=_pick(row.opensubtitles_api_key, config.OPENSUBTITLES_API_KEY),
        subtitle_languages=[lang.strip() for lang in _pick(row.subtitle_languages, config.SUBTITLE_LANGUAGES).split(",") if lang.strip()],
        request_movie_limit=_pick(row.request_movie_limit, config.REQUEST_MOVIE_LIMIT),
        request_series_limit=_pick(row.request_series_limit, config.REQUEST_SERIES_LIMIT),
        request_limit_days=_pick(row.request_limit_days, config.REQUEST_LIMIT_DAYS),
        auth_required=_pick(row.auth_required, config.AUTH_REQUIRED),
        flaresolverr_url=_pick(row.flaresolverr_url, config.FLARESOLVERR_URL),
    )
