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
