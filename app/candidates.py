from sqlalchemy.orm import Session

from app import indexers as indexer_engine
from app.models import QualityProfile
from app.parser import parse_quality
from app.scoring import best_release


async def scored_candidates(db: Session, query: str, profile: QualityProfile | None) -> list[dict]:
    """Search all enabled indexers for `query`, quality-tag every release, and flag the best one."""
    releases = await indexer_engine.search_all(db, query)

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
