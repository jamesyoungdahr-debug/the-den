"""One entry point for "search this indexer": Torznab/Newznab endpoints and the native
public-tracker implementations behind the same call, so candidates.py, the manual search
and the UI never care which kind an `Indexer` row is."""

import asyncio
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import torznab
from app.indexers.catalog import BY_SLUG, PRESETS, as_dicts  # noqa: F401  (re-exported)
from app.indexers.fetch import Fetcher, test_solver  # noqa: F401
from app.indexers.native import NATIVES
from app.models import Indexer, IndexerStat
from app.torznab import Release


def implementation_of(indexer: Indexer) -> str:
    return indexer.implementation or indexer.protocol or "torznab"


def is_native(indexer: Indexer) -> bool:
    return implementation_of(indexer) in NATIVES


def _solver_url(db: Session) -> str:
    from app import settings as settings_module  # local: settings imports the torrent engine

    return settings_module.effective(db).flaresolverr_url or ""


async def search_one(indexer: Indexer, query: str, solver_url: str = "") -> list[Release]:
    impl = implementation_of(indexer)
    if impl in NATIVES:
        return await NATIVES[impl].search(Fetcher(solver_url), indexer.url or NATIVES[impl].url, query)
    return await torznab.search(indexer.url, indexer.api_key, query, indexer.name)


def _record(db: Session, indexer_id: int, ok: bool, ms: int, error: str | None) -> None:
    """Count one search in indexer_stats (per indexer, per UTC day). Never raises."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        stat = db.query(IndexerStat).filter(IndexerStat.indexer_id == indexer_id, IndexerStat.day == day).first()
        if not stat:
            stat = IndexerStat(indexer_id=indexer_id, day=day, searches=0, successes=0, failures=0, total_ms=0)
            db.add(stat)
        stat.searches += 1
        stat.total_ms += ms
        if ok:
            stat.successes += 1
        else:
            stat.failures += 1
            if error:
                stat.last_error = error[:200]
        db.commit()
    except Exception:
        db.rollback()


async def search_all(db: Session, query: str, indexers: list[Indexer] | None = None) -> list[Release]:
    """Search every enabled indexer concurrently; a broken one is skipped, never fatal,
    and every outcome is counted in indexer_stats."""
    if indexers is None:
        indexers = db.query(Indexer).filter(Indexer.enabled == True).all()  # noqa: E712
    solver = _solver_url(db)

    async def safe(ix: Indexer):
        t0 = time.monotonic()
        try:
            result = await search_one(ix, query, solver)
            _record(db, ix.id, True, int((time.monotonic() - t0) * 1000), None)
            return result
        except Exception as exc:
            _record(db, ix.id, False, int((time.monotonic() - t0) * 1000), f"{type(exc).__name__}: {exc}")
            return []

    releases: list[Release] = []
    for chunk in await asyncio.gather(*(safe(i) for i in indexers)):
        releases.extend(chunk)
    return releases


async def test_one(indexer: Indexer, db: Session) -> dict:
    impl = implementation_of(indexer)
    if impl in NATIVES:
        return await NATIVES[impl].test(Fetcher(_solver_url(db)), indexer.url or NATIVES[impl].url)
    return await torznab.test_connection(indexer.url, indexer.api_key)
