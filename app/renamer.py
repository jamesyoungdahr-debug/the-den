"""E4: rename already-imported library files to match the current Plex-naming
convention (app/importer.py only names files at import time, so a title renamed on
TMDB/TVmaze, or a file imported before M13's naming existed, can drift). Filenames
only -- existing folder structure is left alone."""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.importer import episode_name, movie_name
from app.models import Episode, Movie, Series


def movie_plan(movie: Movie) -> dict | None:
    """The rename this movie's file needs, or None if it already matches (or has no file)."""
    if not movie.file_path:
        return None
    current = Path(movie.file_path)
    proposed = current.with_name(movie_name(movie) + current.suffix)
    if proposed == current:
        return None
    return {"kind": "movie", "id": movie.id, "label": movie_name(movie), "current_path": str(current), "proposed_path": str(proposed)}


def episode_plan(series: Series, episode: Episode) -> dict | None:
    """The rename this episode's file needs, or None if it already matches (or has no file)."""
    if not episode.file_path:
        return None
    current = Path(episode.file_path)
    proposed = current.with_name(episode_name(series, episode) + current.suffix)
    if proposed == current:
        return None
    return {"kind": "episode", "id": episode.id, "label": episode_name(series, episode), "current_path": str(current), "proposed_path": str(proposed)}


def all_plans(db: Session) -> list[dict]:
    """Every file in the library whose name doesn't match the current convention."""
    plans = []
    for movie in db.query(Movie).filter(Movie.has_file == True).all():  # noqa: E712
        plan = movie_plan(movie)
        if plan:
            plans.append(plan)
    for episode in db.query(Episode).filter(Episode.has_file == True).all():  # noqa: E712
        series = db.get(Series, episode.series_id)
        if series is None:
            continue
        plan = episode_plan(series, episode)
        if plan:
            plans.append(plan)
    return plans


def _move(current: Path, proposed: Path) -> None:
    """Same-filesystem rename when possible (keeps the inode, so a hardlink to a still-
    seeding torrent copy is unaffected); copy+delete fallback across filesystems, mirroring
    app/importer.py's _link_into hardlink-or-copy style."""
    if not current.exists():
        raise FileNotFoundError(f"{current} not found on disk")
    try:
        current.rename(proposed)
    except OSError:
        shutil.copy2(current, proposed)
        current.unlink()


def apply_plan(db: Session, kind: str, item_id: int) -> dict:
    """Apply one rename and update the title's file_path. Raises ValueError if there's
    nothing to rename, FileNotFoundError/OSError if the move itself fails."""
    if kind == "movie":
        movie = db.get(Movie, item_id)
        plan = movie_plan(movie) if movie else None
        if plan is None:
            raise ValueError("Nothing to rename")
        _move(Path(plan["current_path"]), Path(plan["proposed_path"]))
        movie.file_path = plan["proposed_path"]
        db.commit()
        return plan
    if kind == "episode":
        episode = db.get(Episode, item_id)
        series = db.get(Series, episode.series_id) if episode else None
        plan = episode_plan(series, episode) if episode and series else None
        if plan is None:
            raise ValueError("Nothing to rename")
        _move(Path(plan["current_path"]), Path(plan["proposed_path"]))
        episode.file_path = plan["proposed_path"]
        db.commit()
        return plan
    raise ValueError("kind must be 'movie' or 'episode'")
