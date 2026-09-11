from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String

from app.db import Base


class Indexer(Base):
    """A Torznab/Newznab-compatible indexer we can search for releases."""

    __tablename__ = "indexers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    api_key = Column(String, nullable=True)
    protocol = Column(String, nullable=False, default="torznab")  # torznab | newznab
    enabled = Column(Boolean, nullable=False, default=True)


class QualityProfile(Base):
    """Ranked list of acceptable qualities, best first, e.g. '1080p,720p,480p'."""

    __tablename__ = "quality_profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    allowed_qualities = Column(String, nullable=False)  # comma-separated, best first
    cutoff = Column(String, nullable=False)  # stop searching once this quality is had


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)
    tmdb_id = Column(Integer, nullable=False, unique=True)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    overview = Column(String, nullable=True)
    poster_path = Column(String, nullable=True)
    has_file = Column(Boolean, nullable=False, default=False)
    quality_profile_id = Column(Integer, ForeignKey("quality_profiles.id"), nullable=True)


class Series(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True)
    tvmaze_id = Column(Integer, nullable=False, unique=True)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    overview = Column(String, nullable=True)
    poster_path = Column(String, nullable=True)
    quality_profile_id = Column(Integer, ForeignKey("quality_profiles.id"), nullable=True)


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    season_number = Column(Integer, nullable=False)
    episode_number = Column(Integer, nullable=False)
    title = Column(String, nullable=True)
    air_date = Column(String, nullable=True)
    has_file = Column(Boolean, nullable=False, default=False)


class Settings(Base):
    """Single-row table (id is always 1) of user-editable overrides for app/config.py's
    env-var defaults. A null field here means "use the env-var default"."""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    tmdb_api_key = Column(String, nullable=True)
    movies_root = Column(String, nullable=True)
    tv_root = Column(String, nullable=True)
    automation_interval_seconds = Column(Integer, nullable=True)
    discord_webhook_url = Column(String, nullable=True)
    # Built-in torrent client
    downloads_root = Column(String, nullable=True)
    torrent_port = Column(Integer, nullable=True)
    download_rate_limit_kib = Column(Integer, nullable=True)
    upload_rate_limit_kib = Column(Integer, nullable=True)
    seed_ratio_limit = Column(Float, nullable=True)
    seed_time_limit_minutes = Column(Integer, nullable=True)
    # Plex (M11c): the owner's account + the server The Den is tied to
    plex_token = Column(String, nullable=True)
    plex_owner_id = Column(Integer, nullable=True)
    plex_owner_username = Column(String, nullable=True)
    plex_server_name = Column(String, nullable=True)
    plex_machine_id = Column(String, nullable=True)
    plex_url = Column(String, nullable=True)
    plex_sections = Column(String, nullable=True)  # JSON list of section keys
    plex_allow_any_account = Column(Boolean, nullable=True)


class DownloadRecord(Base):
    __tablename__ = "download_records"

    id = Column(Integer, primary_key=True)
    # Exactly one of these is set, depending on whether this download is a movie or an episode.
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    release_title = Column(String, nullable=False)
    download_url = Column(String, nullable=False)
    # Key into the built-in torrent engine (app/torrent). Null only for records that
    # predate it (they were tracked in an external qBittorrent) -- those can't be
    # advanced any more and get marked failed on their next check.
    info_hash = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="queued")  # queued|downloading|completed|imported|failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class User(Base):
    """An account. Local users have a password_hash; Plex-linked users (M11c) have a
    plex_id and may have no password at all. role is 'admin' or 'user'."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    plex_id = Column(Integer, nullable=True, unique=True)
    plex_username = Column(String, nullable=True)
    role = Column(String, nullable=False, default="user")  # admin | user
    auto_approve = Column(Boolean, nullable=False, default=False)
    movie_limit = Column(Integer, nullable=True)
    series_limit = Column(Integer, nullable=True)
    limit_days = Column(Integer, nullable=True)
    api_token = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime, nullable=True)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def initial(self) -> str:
        return (self.username or "?")[:1].upper()
