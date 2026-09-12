"""One entry point for "search this indexer": Torznab/Newznab endpoints and the native
public-tracker implementations behind the same call, so candidates.py, the manual search
and the UI never care which kind an `Indexer` row is."""

import asyncio

from sqlalchemy.orm import Session

from app import torznab
from app.indexers.catalog import BY_SLUG, PRESETS, as_dicts  # noqa: F401  (re-exported)
from app.indexers.fetch import Fetcher, test_solver  # noqa: F401
from app.indexers.native import NATIVES
from app.models import Indexer
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


async def search_all(db: Session, query: str, indexers: list[Indexer] | None = None) -> list[Release]:
    """Search every enabled indexer concurrently; a broken one is skipped, never fatal."""
    if indexers is None:
        indexers = db.query(Indexer).filter(Indexer.enabled == True).all()  # noqa: E712
    solver = _solver_url(db)

    async def safe(ix: Indexer):
        try:
            return await search_one(ix, query, solver)
        except Exception:
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
