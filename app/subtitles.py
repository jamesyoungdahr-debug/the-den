"""E6: fetch subtitles from OpenSubtitles for movies/episodes missing them in the
configured languages, one per language per title, written as a sibling .srt file next
to the video (Plex's own convention: `Movie (Year).en.srt`)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app import opensubtitles
from app import settings as settings_module
from app.models import Episode, Movie, Series


def subtitle_path(file_path: str, language: str) -> Path:
    p = Path(file_path)
    return p.with_name(p.stem + f".{language}.srt")


def has_subtitle(file_path: str, language: str) -> bool:
    return subtitle_path(file_path, language).exists()


async def _fetch_one(api_key: str, file_path: str, tmdb_id: int, languages: list[str], season_number: int | None = None, episode_number: int | None = None) -> int:
    """Fetch and write whichever configured languages are missing for this file. Returns
    how many were written."""
    missing = [lang for lang in languages if not has_subtitle(file_path, lang)]
    if not missing:
        return 0
    results = await opensubtitles.search(api_key, tmdb_id, missing, season_number, episode_number)
    by_lang: dict[str, dict] = {}
    for r in results:
        by_lang.setdefault(r["language"], r)
    written = 0
    for lang in missing:
        candidate = by_lang.get(lang)
        if not candidate:
            continue
        text = await opensubtitles.download(api_key, candidate["file_id"])
        subtitle_path(file_path, lang).write_text(text, encoding="utf-8")
        written += 1
    return written


async def fetch_missing(db: Session) -> dict:
    """One pass over the library: fetch missing subtitles for every movie/episode that
    has a file and a TMDB id, in the configured languages. No-ops cleanly (returns
    zeros) when no OpenSubtitles API key is configured."""
    s = settings_module.effective(db)
    result = {"fetched": 0, "skipped_no_key": not bool(s.opensubtitles_api_key)}
    if not s.opensubtitles_api_key or not s.subtitle_languages:
        return result
    for movie in db.query(Movie).filter(Movie.has_file == True).all():  # noqa: E712
        if not movie.file_path or not movie.tmdb_id:
            continue
        try:
            result["fetched"] += await _fetch_one(s.opensubtitles_api_key, movie.file_path, movie.tmdb_id, s.subtitle_languages)
        except Exception:
            pass
    for episode in db.query(Episode).filter(Episode.has_file == True).all():  # noqa: E712
        if not episode.file_path:
            continue
        series = db.get(Series, episode.series_id)
        if series is None or not series.tmdb_id:
            continue
        try:
            result["fetched"] += await _fetch_one(s.opensubtitles_api_key, episode.file_path, series.tmdb_id, s.subtitle_languages, episode.season_number, episode.episode_number)
        except Exception:
            pass
    return result
