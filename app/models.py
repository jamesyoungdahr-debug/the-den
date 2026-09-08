from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

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
    tmdb_id = Column(Integer, nullable=False, unique=True)
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


class DownloadRecord(Base):
    __tablename__ = "download_records"

    id = Column(Integer, primary_key=True)
    # Exactly one of these is set, depending on whether this download is a movie or an episode.
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    release_title = Column(String, nullable=False)
    download_url = Column(String, nullable=False)
    category = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")  # queued|downloading|completed|imported|failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
