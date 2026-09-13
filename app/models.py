from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from app.db import Base


class Indexer(Base):
    """A Torznab/Newznab-compatible indexer we can search for releases."""

    __tablename__ = "indexers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    api_key = Column(String, nullable=True)
    protocol = Column(String, nullable=False, default="torznab")  # torznab | newznab | native
    # torznab | newznab | a native public-tracker slug (app/indexers/native.py); catalog preset it came from
    implementation = Column(String, nullable=True)
    preset = Column(String, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)


class QualityProfile(Base):
    """Ranked list of acceptable qualities, best first, e.g. '1080p,720p,480p'."""

    __tablename__ = "quality_profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    allowed_qualities = Column(String, nullable=False)  # comma-separated, best first
    cutoff = Column(String, nullable=False)  # stop searching once this quality is had
    min_format_score = Column(Integer, nullable=False, default=0)  # releases scoring below this are rejected
    upgrade_until_score = Column(Integer, nullable=False, default=0)  # keep upgrading a title's file until its format score reaches this (0 = quality cutoff only)


class RootFolder(Base):
    """A named library folder (E2): Movies vs Kids Movies, 4K vs 1080p, etc. Falls back to
    Settings.movies_root/tv_root when a title has none and no default is marked."""

    __tablename__ = "root_folders"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    media_type = Column(String, nullable=False)  # movie | tv
    path = Column(String, nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)
    tmdb_id = Column(Integer, nullable=False, unique=True)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    overview = Column(String, nullable=True)
    poster_path = Column(String, nullable=True)
    has_file = Column(Boolean, nullable=False, default=False)
    file_quality = Column(String, nullable=True)  # quality of the file on disk, from the imported release title
    file_score = Column(Integer, nullable=False, default=0)  # its custom-format score at import time
    file_path = Column(String, nullable=True)  # the library file the last import wrote
    last_upgrade_search = Column(DateTime, nullable=True)
    quality_profile_id = Column(Integer, ForeignKey("quality_profiles.id"), nullable=True)
    root_folder_id = Column(Integer, ForeignKey("root_folders.id"), nullable=True)


class Series(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True)
    tvmaze_id = Column(Integer, nullable=False, unique=True)
    tmdb_id = Column(Integer, nullable=True, index=True)  # set when added from Discover (M11d)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    overview = Column(String, nullable=True)
    poster_path = Column(String, nullable=True)
    quality_profile_id = Column(Integer, ForeignKey("quality_profiles.id"), nullable=True)
    root_folder_id = Column(Integer, ForeignKey("root_folders.id"), nullable=True)


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    season_number = Column(Integer, nullable=False)
    episode_number = Column(Integer, nullable=False)
    title = Column(String, nullable=True)
    air_date = Column(String, nullable=True)
    has_file = Column(Boolean, nullable=False, default=False)
    file_quality = Column(String, nullable=True)  # quality of the file on disk, from the imported release title
    file_score = Column(Integer, nullable=False, default=0)  # its custom-format score at import time
    file_path = Column(String, nullable=True)  # the library file the last import wrote
    last_upgrade_search = Column(DateTime, nullable=True)
    # Automation only grabs monitored episodes; a season request monitors just its seasons.
    monitored = Column(Boolean, nullable=False, default=True)


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
    plex_scan_interval_minutes = Column(Integer, nullable=True)
    import_list_interval_minutes = Column(Integer, nullable=True)
    opensubtitles_api_key = Column(String, nullable=True)
    subtitle_languages = Column(String, nullable=True)  # comma-separated language codes, e.g. "en,es"
    plex_last_scan_at = Column(DateTime, nullable=True)
    plex_last_scan_result = Column(String, nullable=True)
    # Request quotas (M11g): how many movies / series a non-admin may request per window.
    # Null = env default; 0 = unlimited. Per-user overrides live on User.
    request_movie_limit = Column(Integer, nullable=True)
    request_series_limit = Column(Integer, nullable=True)
    request_limit_days = Column(Integer, nullable=True)
    # FlareSolverr / Byparr base URL for Cloudflare-fronted public trackers (M12)
    flaresolverr_url = Column(String, nullable=True)
    # Null = follow the AUTH_REQUIRED env var; set from Settings -> Accounts.
    auth_required = Column(Boolean, nullable=True)


class DownloadRecord(Base):
    __tablename__ = "download_records"

    id = Column(Integer, primary_key=True)
    # One of movie_id, episode_id or (series_id + season_number) is set.
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    # A season pack sets these instead of episode_id: every episode file in the torrent is imported.
    series_id = Column(Integer, ForeignKey("series.id"), nullable=True)
    season_number = Column(Integer, nullable=True)
    release_title = Column(String, nullable=False)
    download_url = Column(String, nullable=False)
    # Key into the built-in torrent engine (app/torrent). Null only for records that
    # predate it (they were tracked in an external qBittorrent) -- those can't be
    # advanced any more and get marked failed on their next check.
    info_hash = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="queued")  # queued|downloading|completed|imported|failed
    quality = Column(String, nullable=True)  # parsed from release_title when grabbed
    score = Column(Integer, nullable=False, default=0)  # custom-format score when grabbed
    upgrade = Column(Boolean, nullable=False, default=False)  # replaces an existing file when imported
    failure_reason = Column(String, nullable=True)  # why status became failed (stalled, dead, error, blocklisted by hand)
    unmatched_files = Column(Text, nullable=True)  # JSON list of file names in the torrent that couldn't be placed automatically (M23)
    last_progress = Column(Float, nullable=False, default=0.0)  # 0..1 at the last check
    last_progress_at = Column(DateTime, nullable=True)  # when progress last moved
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


class PlexMedia(Base):
    """What the owner's Plex server has, as of the last scan (M11e). Matched to TMDB cards
    by tmdb_id (or tvdb_id for series). seasons is JSON {season_number: episode_count}."""

    __tablename__ = "plex_media"

    id = Column(Integer, primary_key=True)
    media_type = Column(String, nullable=False)  # movie | tv
    rating_key = Column(String, nullable=False, unique=True)
    tmdb_id = Column(Integer, nullable=True, index=True)
    tvdb_id = Column(Integer, nullable=True, index=True)
    imdb_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    seasons = Column(String, nullable=True)
    thumb = Column(String, nullable=True)  # poster path on the PMS, served via /api/plex/thumb/{rating_key}
    scanned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MediaRequest(Base):
    """A user asking for a movie or for seasons of a series (M11f). Approval turns it into
    library rows (movie_id / series_id); availability is derived from those, not stored."""

    __tablename__ = "media_requests"

    id = Column(Integer, primary_key=True)
    media_type = Column(String, nullable=False)  # movie | tv
    tmdb_id = Column(Integer, nullable=False, index=True)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    poster_path = Column(String, nullable=True)
    seasons = Column(String, nullable=True)  # JSON list of season numbers; empty/null = whole series
    status = Column(String, nullable=False, default="pending")  # pending | approved | available | declined
    note = Column(String, nullable=True)
    available_at = Column(DateTime, nullable=True)  # set when an approved request is found to be fulfilled
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def season_list(self) -> list[int]:
        import json as _json
        return _json.loads(self.seasons) if self.seasons else []


class NotificationAgent(Base):
    """A place notifications go (M15); one row per Discord webhook, ntfy topic, etc."""

    __tablename__ = "notification_agents"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False)  # discord | ntfy | webhook | telegram | pushover
    config = Column(String, nullable=True)  # JSON object with the kind's fields, see app/notifier.KINDS
    events = Column(String, nullable=True)  # JSON list of event keys; null/empty = every event
    enabled = Column(Boolean, nullable=False, default=True)


class ImportList(Base):
    """A place to auto-add movies/series from (E1): a TMDB list or a Plex watchlist, synced on a schedule."""

    __tablename__ = "import_lists"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False)  # tmdb_list | plex_watchlist
    config = Column(String, nullable=True)  # JSON object with the kind's fields (e.g. {"list_id": "..."} for tmdb_list)
    quality_profile_id = Column(Integer, ForeignKey("quality_profiles.id"), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    last_result = Column(String, nullable=True)  # e.g. "3 added, 12 already in the library"


class IndexerStat(Base):
    """Per-indexer, per-day search counters (M16): what the health check and the Indexers page read."""

    __tablename__ = "indexer_stats"

    id = Column(Integer, primary_key=True)
    indexer_id = Column(Integer, ForeignKey("indexers.id", ondelete="CASCADE"), nullable=False)
    day = Column(String, nullable=False)  # YYYY-MM-DD, UTC
    searches = Column(Integer, nullable=False, default=0)
    successes = Column(Integer, nullable=False, default=0)
    failures = Column(Integer, nullable=False, default=0)
    total_ms = Column(Integer, nullable=False, default=0)
    last_error = Column(String, nullable=True)


class HealthIssue(Base):
    """A currently-open health problem (M16); rows come and go as app/health.py re-checks."""

    __tablename__ = "health_issues"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    level = Column(String, nullable=False)  # warning | error
    message = Column(String, nullable=False)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)


class CustomFormat(Base):
    """A named release-title rule set (M17): rules is a JSON list of
    {"field": "title"|"group"|"language"|"source", "op": "contains"|"regex", "value": str, "negate": bool}.
    A release matches the format when every rule matches."""

    __tablename__ = "custom_formats"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    rules = Column(Text, nullable=False, default="[]")  # JSON list
    builtin = Column(Boolean, nullable=False, default=False)


class ProfileFormatScore(Base):
    """Score a quality profile gives a custom format; missing row means 0."""

    __tablename__ = "profile_format_scores"
    __table_args__ = (UniqueConstraint("profile_id", "format_id", name="uq_profile_format"),)

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("quality_profiles.id", ondelete="CASCADE"), nullable=False)
    format_id = Column(Integer, ForeignKey("custom_formats.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, nullable=False, default=0)


class BlocklistEntry(Base):
    """A release automation must not grab again (M19): matched by info hash or exact
    title. Expires so a temporarily dead torrent can be retried later."""

    __tablename__ = "blocklist"

    id = Column(Integer, primary_key=True)
    info_hash = Column(String, nullable=True, index=True)
    release_title = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="SET NULL"), nullable=True)
    episode_id = Column(Integer, ForeignKey("episodes.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)


class HistoryEvent(Base):
    """One thing that happened to a title (E5): grabbed, imported, upgraded, a download
    that failed, or a torrent removed. Per-title history on the detail page reads this."""

    __tablename__ = "history_events"

    id = Column(Integer, primary_key=True)
    event = Column(String, nullable=False)  # grabbed | upgraded | imported | download_failed | removed
    release_title = Column(String, nullable=False)
    message = Column(String, nullable=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=True)
    season_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
