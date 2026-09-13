from collections.abc import Callable
from sqlalchemy.orm import Session

from app import blocklist
from app import formats
from app import indexers as indexer_engine
from app.models import Episode, Movie, QualityProfile, Series
from app.parser import parse_quality, parse_season_pack
from app.torznab import Release
from app.scoring import best_release



def profile_for(db: Session, quality_profile_id: int | None, default: QualityProfile | None = None) -> QualityProfile | None:
    """The title's own profile, else `default` (the automation cycle passes the default profile
    so it is not re-queried per title), else the first profile in the table."""
    return db.get(QualityProfile, quality_profile_id) if quality_profile_id else default or db.query(QualityProfile).first()


def movie_query(movie: Movie) -> str:
    """Indexer query for a movie: title plus year when known."""
    return f"{movie.title} {movie.year}" if movie.year else movie.title


def episode_query(series: Series, episode: Episode) -> str:
    """Indexer query for an episode: the SxxEyy form is what indexers expect."""
    return f"{series.title} S{episode.season_number:02d}E{episode.episode_number:02d}"


def season_query(series: Series, season_number: int) -> str:
    """Indexer query for a whole season: `Show S01` is the form season packs are named after."""
    return f"{series.title} S{season_number:02d}"


async def scored_candidates(db: Session, query: str, profile: QualityProfile | None, keep: Callable[[Release], bool] | None = None) -> list[dict]:
    """Search all enabled indexers for `query`, quality-tag every release, and flag the best one.
    `keep` drops releases before scoring (season packs use it)."""
    releases = await indexer_engine.search_all(db, query)
    keys = blocklist.blocked_keys(db)
    releases = [r for r in releases if not blocklist.is_blocked(r.title, r.download_url, keys)]

    if keep is not None:
        releases = [r for r in releases if keep(r)]

    scored_formats = formats.profile_scores(db, profile) if profile else []
    details = {r.title: formats.score_title(r.title, scored_formats) for r in releases}   # title -> (score, [format names])
    best = best_release(releases, profile, {t: d[0] for t, d in details.items()}) if profile else None

    scored = [
        {
            "title": r.title,
            "download_url": r.download_url,
            "indexer_name": r.indexer_name,
            "size": r.size,
            "seeders": r.seeders,
            "peers": r.peers,
            "quality": parse_quality(r.title),
            "score": details[r.title][0],
            "formats": details[r.title][1],
            "is_best": r is best,
        }
        for r in releases
    ]
    scored.sort(key=lambda r: (not r["is_best"], -r["score"], -(r["seeders"] or 0)))
    return scored


async def season_candidates(db: Session, series: Series, season_number: int, profile: QualityProfile | None) -> list[dict]:
    """Releases that are whole-season packs for this season, scored like any candidate."""
    return await scored_candidates(db, season_query(series, season_number), profile, keep=lambda r: parse_season_pack(r.title) == season_number)
