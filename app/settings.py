from dataclasses import dataclass

from sqlalchemy.orm import Session

from app import config
from app.models import Settings

SETTINGS_ROW_ID = 1


@dataclass
class EffectiveSettings:
    tmdb_api_key: str
    qbit_url: str
    qbit_username: str
    qbit_password: str
    movies_root: str
    tv_root: str
    automation_interval_seconds: int
    discord_webhook_url: str


def get_row(db: Session) -> Settings:
    row = db.get(Settings, SETTINGS_ROW_ID)
    if not row:
        row = Settings(id=SETTINGS_ROW_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def effective(db: Session) -> EffectiveSettings:
    """DB overrides layered on top of app/config.py's env-var defaults."""
    row = get_row(db)
    return EffectiveSettings(
        tmdb_api_key=row.tmdb_api_key or config.TMDB_API_KEY,
        qbit_url=row.qbit_url or config.QBIT_URL,
        qbit_username=row.qbit_username or config.QBIT_USERNAME,
        qbit_password=row.qbit_password or config.QBIT_PASSWORD,
        movies_root=row.movies_root or config.MOVIES_ROOT,
        tv_root=row.tv_root or config.TV_ROOT,
        automation_interval_seconds=row.automation_interval_seconds or config.AUTOMATION_INTERVAL_SECONDS,
        discord_webhook_url=row.discord_webhook_url or config.DISCORD_WEBHOOK_URL,
    )
