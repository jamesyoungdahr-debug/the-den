"""Client for qBittorrent's WebUI API (https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API).

We track downloads by category rather than info-hash: adding a torrent only
returns "Ok." with no id, so each grab gets its own category
(the-den-movie-<id>) and we look it up that way afterward.
"""

import httpx

from app import config


async def _client() -> httpx.AsyncClient:
    client = httpx.AsyncClient(base_url=config.QBIT_URL, timeout=15)
    resp = await client.post(
        "/api/v2/auth/login",
        data={"username": config.QBIT_USERNAME, "password": config.QBIT_PASSWORD},
    )
    resp.raise_for_status()
    return client


async def add_torrent(download_url: str, category: str) -> None:
    client = await _client()
    try:
        resp = await client.post(
            "/api/v2/torrents/add",
            data={"urls": download_url, "category": category},
        )
        resp.raise_for_status()
    finally:
        await client.aclose()


async def get_by_category(category: str) -> dict | None:
    """Return the first torrent's info dict for this category, or None if not found yet."""
    client = await _client()
    try:
        resp = await client.get("/api/v2/torrents/info", params={"category": category})
        resp.raise_for_status()
        torrents = resp.json()
        return torrents[0] if torrents else None
    finally:
        await client.aclose()
