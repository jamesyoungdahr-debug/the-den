"""Client for TVmaze (https://www.tvmaze.com/api) — free, no API key or account needed.
Used for TV metadata instead of TMDB so adding a series doesn't need a second signup."""

import re

import httpx

from app import config


def _strip_html(text: str | None) -> str | None:
    return re.sub(r"<[^>]+>", "", text).strip() if text else None


async def search_tv(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{config.TVMAZE_BASE_URL}/search/shows", params={"q": query})
        resp.raise_for_status()
        results = resp.json()

    candidates = []
    for item in results:
        show = item["show"]
        premiered = show.get("premiered") or ""
        candidates.append(
            {
                "tvmaze_id": show["id"],
                "title": show["name"],
                "year": int(premiered[:4]) if premiered[:4].isdigit() else None,
                "overview": _strip_html(show.get("summary")),
                "poster_path": (show.get("image") or {}).get("medium"),
            }
        )
    return candidates


def _normalize_show(show: dict) -> dict:
    premiered = show.get("premiered") or ""
    return {
        "tvmaze_id": show["id"],
        "title": show["name"],
        "year": int(premiered[:4]) if premiered[:4].isdigit() else None,
        "overview": _strip_html(show.get("summary")),
        "poster_path": (show.get("image") or {}).get("medium"),
        "tvdb_id": (show.get("externals") or {}).get("thetvdb"),
        "imdb_id": (show.get("externals") or {}).get("imdb"),
    }


async def lookup_show(*, thetvdb: int | None = None, imdb: str | None = None) -> dict | None:
    """Find a TVmaze show by an external id (TVmaze answers with a 301 to the show). Used
    to map a TMDB series to its TVmaze episode list when adding from Discover."""
    params = {"thetvdb": thetvdb} if thetvdb else {"imdb": imdb} if imdb else None
    if not params:
        return None
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        resp = await client.get(f"{config.TVMAZE_BASE_URL}/lookup/shows", params=params)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _normalize_show(resp.json())


async def find_show(title: str, year: int | None) -> dict | None:
    """Name search fallback: the first result whose title matches (and year, when known)."""
    candidates = await search_tv(title)
    same_title = [c for c in candidates if c["title"].lower() == title.lower()]
    if year:
        same_year = [c for c in same_title if c["year"] == year]
        if same_year:
            return same_year[0]
    return same_title[0] if same_title else None


async def get_tv_episodes(tvmaze_id: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{config.TVMAZE_BASE_URL}/shows/{tvmaze_id}/episodes")
        resp.raise_for_status()
        episodes = resp.json()

    return [
        {
            "season_number": ep["season"],
            "episode_number": ep["number"],
            "title": ep.get("name"),
            "air_date": ep.get("airdate"),
        }
        for ep in episodes
        if ep.get("season") and ep.get("number")  # skip specials with no season/number
    ]
