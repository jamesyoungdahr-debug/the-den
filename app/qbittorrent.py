"""Client for qBittorrent's WebUI API (https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API).

We track downloads by category rather than info-hash: adding a torrent only
returns "Ok." with no id, so each grab gets its own category
(the-den-movie-<id>) and we look it up that way afterward.
"""

import httpx


async def _client(url: str, username: str, password: str) -> httpx.AsyncClient:
    client = httpx.AsyncClient(base_url=url, timeout=15)
    resp = await client.post("/api/v2/auth/login", data={"username": username, "password": password})
    resp.raise_for_status()
    # qBittorrent's login endpoint always returns 200 -- "Ok." on success, "Fails."
    # on bad credentials -- so raise_for_status() can never catch a login failure.
    if resp.text.strip() != "Ok.":
        await client.aclose()
        raise RuntimeError("qBittorrent login failed -- check the configured username/password")
    return client


async def add_torrent(download_url: str, category: str, *, url: str, username: str, password: str) -> None:
    client = await _client(url, username, password)
    try:
        resp = await client.post(
            "/api/v2/torrents/add",
            data={"urls": download_url, "category": category},
        )
        resp.raise_for_status()
    finally:
        await client.aclose()


async def get_by_category(category: str, *, url: str, username: str, password: str) -> dict | None:
    """Return the first torrent's info dict for this category, or None if not found yet."""
    client = await _client(url, username, password)
    try:
        resp = await client.get("/api/v2/torrents/info", params={"category": category})
        resp.raise_for_status()
        torrents = resp.json()
        return torrents[0] if torrents else None
    finally:
        await client.aclose()
