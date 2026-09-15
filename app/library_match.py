"""M50b - place the files the scan recorded but could not identify.
The scan ties a file to a title The Den already knows; this covers the rest,
searching TMDB with the parsed name. A file is attached only when exactly ONE
candidate fits, because guessing between same-named titles would file the wrong
metadata against someone's media; anything ambiguous is left for a person to
place in the unmatched queue."""

from __future__ import annotations

import logging
import os

from sqlalchemy.orm import Session

from app import settings as settings_module, tmdb
from app.library_scan import SEASON_DIR_RE, _norm as normalise_title
from app.models import Episode, MediaFile
from app.parser import parse_episode, parse_movie
from app.requests_service import get_or_create_movie, get_or_create_series

log = logging.getLogger(__name__)


# TMDB release dates slip by a year between regions and festivals, so a year alone is weak evidence.
YEAR_SLACK = 1


def _close_year(candidate: int | None, wanted: int | None) -> bool:
    """A year only argues against a candidate when BOTH sides have one and they disagree."""
    if wanted is None or candidate is None:
        return True
    return abs(int(candidate) - int(wanted)) <= YEAR_SLACK


def _name_and_folder(path: str) -> tuple[str, str]:
    """Return (file stem without extension, containing folder name)."""
    basename = os.path.basename(path)
    stem, _ = os.path.splitext(basename)
    folder = os.path.basename(os.path.dirname(path))
    return stem, folder


async def movie_tmdb_id(path: str, api_key: str) -> int | None:
    """The one TMDB movie this file's name clearly means, or None when the field is ambiguous."""
    stem, folder = _name_and_folder(path)

    # Parse the file stem first
    parsed_title, parsed_year = parse_movie(stem) or (None, None)

    # If we got no result or no year, also try the folder name — the importer stores movies as
    # movies_root/"Title (Year)"/"Title (Year).ext", so the folder often carries the year the
    # file name left out. Prefer the folder result when it has a year.
    if parsed_title is None or parsed_year is None:
        folder_parsed = parse_movie(folder)
        if folder_parsed and folder_parsed[1] is not None:
            parsed_title, parsed_year = folder_parsed

    if parsed_title is None:
        return None

    # Normalise the title for comparison; empty means nothing useful was parsed
    normed = normalise_title(parsed_title)
    if not normed:
        return None

    cards = await tmdb.search_movie(parsed_title, api_key)

    # Keep only candidates whose normalised title matches and whose year is close enough
    survivors = [
        card for card in cards
        if normalise_title(card.get("title")) == normed
        and _close_year(card.get("year"), parsed_year)
    ]

    # Exactly one match means we can confidently attach the file; anything else is ambiguous
    if len(survivors) == 1:
        return int(survivors[0]["tmdb_id"])
    return None


async def match_movies(db: Session, limit: int = 50) -> dict:
    """Try to place unmatched movie files. Returns counts; the CALLER commits."""
    settings = settings_module.effective(db)
    api_key = settings.tmdb_api_key

    if not api_key:
        return {"tried": 0, "matched": 0, "reason": "no TMDB key"}

    rows = (
        db.query(MediaFile)
        .filter_by(matched=False, missing=False, media_type="movie")
        .order_by(MediaFile.id)
        .limit(limit)
        .all()
    )

    matched = 0
    for row in rows:
        tmdb_id = await movie_tmdb_id(row.path, api_key)
        if tmdb_id is None:
            continue

        movie, _created = await get_or_create_movie(db, tmdb_id)
        row.movie_id = movie.id
        row.episode_id = None
        row.matched = True
        matched += 1

    if matched:
        log.info("library match: placed %d of %d unmatched movie file(s)", matched, len(rows))

    return {"tried": len(rows), "matched": matched}


async def tv_tmdb_id(path: str, api_key: str) -> int | None:
    """The one TMDB series this file's folder clearly means, or None when the field is ambiguous.

    Episode files sit at tv_root/<Series>/Season 01/<Series> - S01E02.ext, so the series name is
    the containing folder, or its parent when that folder is a season folder."""
    folder = os.path.basename(os.path.dirname(path))
    if SEASON_DIR_RE.match(folder):
        folder = os.path.basename(os.path.dirname(os.path.dirname(path)))
    wanted = normalise_title(folder)
    if not wanted:
        return None
    # There is no TV-only search endpoint here, so search everything and keep the series.
    fits = [
        card for card in await tmdb.search_multi(folder, api_key)
        if card.get("media_type") == "tv" and normalise_title(card.get("title")) == wanted
    ]
    if len(fits) != 1:
        return None
    return int(fits[0]["tmdb_id"])


async def match_episodes(db: Session, limit: int = 50) -> dict:
    """Try to place unmatched TV files. Returns counts; the CALLER commits."""
    settings = settings_module.effective(db)
    api_key = settings.tmdb_api_key
    if not api_key:
        return {"tried": 0, "matched": 0, "reason": "no TMDB key"}

    rows = (
        db.query(MediaFile)
        .filter_by(matched=False, missing=False, media_type="tv")
        .order_by(MediaFile.id)
        .limit(limit)
        .all()
    )

    matched = 0
    for row in rows:
        tmdb_id = await tv_tmdb_id(row.path, api_key)
        if tmdb_id is None:
            continue

        series, _created = await get_or_create_series(db, tmdb_id)
        if series is None:
            continue

        parsed = parse_episode(os.path.basename(row.path))
        if parsed is None:
            continue
        season, episode = parsed

        target = (
            db.query(Episode)
            .filter(Episode.series_id == series.id, Episode.season_number == season, Episode.episode_number == episode)
            .first()
        )
        if target is None:
            # The show exists now but this episode does not; the next scan places the file.
            continue

        row.episode_id = target.id
        row.movie_id = None
        row.matched = True
        matched += 1

    if matched:
        log.info("library match: placed %d of %d unmatched TV file(s)", matched, len(rows))

    return {"tried": len(rows), "matched": matched}


async def search_titles(query: str, api_key: str) -> list[dict]:
    """Movie and TV candidates for a query a person typed, for the unmatched queue page.
    Unlike the automatic matcher this makes no judgement - it just shows what TMDB has."""
    cards = await tmdb.search_multi(query, api_key)
    return [card for card in cards if card.get("media_type") in ("movie", "tv")]


async def attach_choice(db: Session, file_id: int, tmdb_id: int, media_type: str) -> bool:
    """Attach one unmatched file to the title a person picked by hand. Returns False when the
    file or the title could not be resolved, so the caller can say so. The CALLER commits."""
    row = db.get(MediaFile, file_id)
    if row is None:
        return False

    if media_type == "movie":
        movie, _created = await get_or_create_movie(db, tmdb_id)
        row.movie_id = movie.id
        row.episode_id = None
        row.matched = True
        return True

    if media_type == "tv":
        series, _created = await get_or_create_series(db, tmdb_id)
        if series is None:
            return False
        parsed = parse_episode(os.path.basename(row.path))
        if parsed is None:
            return False
        season, episode = parsed
        target = (
            db.query(Episode)
            .filter(Episode.series_id == series.id, Episode.season_number == season, Episode.episode_number == episode)
            .first()
        )
        if target is None:
            # The show is now in the library but this episode is not one of its rows.
            return False
        row.episode_id = target.id
        row.movie_id = None
        row.matched = True
        return True

    return False
