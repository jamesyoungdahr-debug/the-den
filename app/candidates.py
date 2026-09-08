from sqlalchemy.orm import Session

from app.models import Indexer, QualityProfile
from app.parser import parse_quality
from app.scoring import best_release
from app.torznab import search as torznab_search


async def scored_candidates(db: Session, query: str, profile: QualityProfile | None) -> list[dict]:
    """Search all enabled indexers for `query`, quality-tag every release, and flag the best one."""
    indexers = db.query(Indexer).filter(Indexer.enabled == True).all()  # noqa: E712
    releases = []
    for indexer in indexers:
        try:
            releases.extend(await torznab_search(indexer.url, indexer.api_key, query, indexer.name))
        except Exception:
            pass  # one broken indexer shouldn't blank out the whole search

    best = best_release(releases, profile) if profile else None

    scored = [
        {
            "title": r.title,
            "download_url": r.download_url,
            "indexer_name": r.indexer_name,
            "size": r.size,
            "seeders": r.seeders,
            "peers": r.peers,
            "quality": parse_quality(r.title),
            "is_best": r is best,
        }
        for r in releases
    ]
    scored.sort(key=lambda r: (not r["is_best"], -(r["seeders"] or 0)))
    return scored
