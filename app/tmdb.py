"""TMDB client. Movie search (used since M2), and for Discover (M11d) the trending /
popular / upcoming rails, multi-search, and movie + TV detail pages.

Every call goes through one cached GET: rails are cached 10 minutes, searches 5, details
an hour. TMDB's own limit (~50 requests/s) is generous; the cache is about not re-fetching
the same five rails on every page view. Results are normalised to one card shape:

    {media_type: "movie"|"tv", tmdb_id, title, year, overview, poster_path, backdrop_path,
     rating, date}

so templates and the companion apps render movies and series with the same code.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app import config

RAIL_TTL = 600
SEARCH_TTL = 300
DETAIL_TTL = 3600
_MAX_CACHE = 600

_cache: dict[str, tuple[float, Any]] = {}


async def _get(path: str, api_key: str, params: dict | None = None, ttl: int = RAIL_TTL) -> Any:
    params = dict(params or {})
    key = f"{path}?" + "&".join(f"{k}={v}" for k, v in sorted(params.items())) + f"#{api_key[-4:]}"
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and hit[0] > now:
        return hit[1]
    async with httpx.AsyncClient(timeout=12) as client:
        resp = await client.get(f"{config.TMDB_BASE_URL}{path}", params={"api_key": api_key, **params})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
    if len(_cache) >= _MAX_CACHE:
        for k in [k for k, (exp, _) in _cache.items() if exp <= now]:
            _cache.pop(k, None)
        if len(_cache) >= _MAX_CACHE:
            _cache.pop(next(iter(_cache)))
    _cache[key] = (now + ttl, data)
    return data


def _year(date: str | None) -> int | None:
    date = date or ""
    return int(date[:4]) if date[:4].isdigit() else None


def normalize(item: dict, media_type: str | None = None) -> dict | None:
    """One card shape for movies and series; None for people and anything else."""
    kind = media_type or item.get("media_type")
    if kind == "movie":
        title, date = item.get("title") or item.get("original_title"), item.get("release_date")
    elif kind == "tv":
        title, date = item.get("name") or item.get("original_name"), item.get("first_air_date")
    else:
        return None
    if not title:
        return None
    return {
        "media_type": kind,
        "tmdb_id": item["id"],
        "title": title,
        "year": _year(date),
        "date": date or None,
        "overview": item.get("overview") or None,
        "poster_path": item.get("poster_path"),
        "backdrop_path": item.get("backdrop_path"),
        "rating": round(item.get("vote_average") or 0, 1) or None,
    }


def _cards(data: dict | None, media_type: str | None = None) -> list[dict]:
    if not data:
        return []
    return [c for c in (normalize(r, media_type) for r in data.get("results", [])) if c]


# ---- search (v1 shape kept for the library pages and companion apps) ---------------

async def search_movie(query: str, api_key: str) -> list[dict]:
    data = await _get("/search/movie", api_key, {"query": query}, ttl=SEARCH_TTL)
    results = []
    for item in (data or {}).get("results", []):
        results.append({
            "tmdb_id": item["id"],
            "title": item["title"],
            "year": _year(item.get("release_date")),
            "overview": item.get("overview"),
            "poster_path": item.get("poster_path"),
        })
    return results


async def search_multi(query: str, api_key: str) -> list[dict]:
    return _cards(await _get("/search/multi", api_key, {"query": query, "include_adult": "false"}, ttl=SEARCH_TTL))


async def get_list(list_id: str, api_key: str) -> list[dict]:
    """A TMDB v3 list's items, normalized. v3 lists are movies-only (TMDB's v4 "combined"
    lists need a user access token, not just an API key, so this stays v3 for now)."""
    data = await _get(f"/list/{list_id}", api_key, ttl=RAIL_TTL)
    if not data:
        return []
    return [c for c in (normalize(item, "movie") for item in data.get("items", [])) if c]


# ---- rails ---------------------------------------------------------------------------

async def trending(api_key: str, window: str = "week", page: int = 1) -> list[dict]:
    return _cards(await _get(f"/trending/all/{window}", api_key, {"page": page}))


async def trending_movies(api_key: str, page: int = 1) -> list[dict]:
    return _cards(await _get("/trending/movie/week", api_key, {"page": page}), "movie")


async def trending_tv(api_key: str, page: int = 1) -> list[dict]:
    return _cards(await _get("/trending/tv/week", api_key, {"page": page}), "tv")


async def popular_movies(api_key: str, page: int = 1) -> list[dict]:
    return _cards(await _get("/movie/popular", api_key, {"page": page}), "movie")


async def upcoming_movies(api_key: str, page: int = 1) -> list[dict]:
    return _cards(await _get("/movie/upcoming", api_key, {"page": page}), "movie")


async def top_rated_movies(api_key: str, page: int = 1) -> list[dict]:
    return _cards(await _get("/movie/top_rated", api_key, {"page": page}), "movie")


async def popular_tv(api_key: str, page: int = 1) -> list[dict]:
    return _cards(await _get("/tv/popular", api_key, {"page": page}), "tv")


async def on_the_air(api_key: str, page: int = 1) -> list[dict]:
    return _cards(await _get("/tv/on_the_air", api_key, {"page": page}), "tv")


async def top_rated_tv(api_key: str, page: int = 1) -> list[dict]:
    return _cards(await _get("/tv/top_rated", api_key, {"page": page}), "tv")


# ---- details ---------------------------------------------------------------------------

def _common_details(d: dict, kind: str) -> dict:
    card = normalize(d, kind) or {}
    videos = (d.get("videos") or {}).get("results", [])
    trailer = next((v for v in videos if v.get("site") == "YouTube" and v.get("type") == "Trailer"), None)
    external = d.get("external_ids") or {}
    card.update({
        "genres": [g["name"] for g in d.get("genres", []) if g.get("name")],
        "tagline": d.get("tagline") or None,
        "status": d.get("status"),
        "vote_count": d.get("vote_count") or 0,
        "imdb_id": external.get("imdb_id") or d.get("imdb_id"),
        "cast": [
            {"name": c.get("name"), "character": c.get("character"), "profile_path": c.get("profile_path")}
            for c in (d.get("credits") or {}).get("cast", [])[:10]
        ],
        "trailer_key": trailer["key"] if trailer else None,
        "recommendations": _cards(d.get("recommendations"), kind)[:12],
    })
    return card


async def movie_details(tmdb_id: int, api_key: str) -> dict | None:
    d = await _get(f"/movie/{tmdb_id}", api_key, {"append_to_response": "credits,videos,recommendations,external_ids"}, ttl=DETAIL_TTL)
    if not d:
        return None
    card = _common_details(d, "movie")
    card["runtime"] = d.get("runtime") or None
    return card


async def tv_details(tmdb_id: int, api_key: str) -> dict | None:
    d = await _get(f"/tv/{tmdb_id}", api_key, {"append_to_response": "credits,videos,recommendations,external_ids"}, ttl=DETAIL_TTL)
    if not d:
        return None
    card = _common_details(d, "tv")
    external = d.get("external_ids") or {}
    card.update({
        "tvdb_id": external.get("tvdb_id"),
        "number_of_seasons": d.get("number_of_seasons") or 0,
        "number_of_episodes": d.get("number_of_episodes") or 0,
        "networks": [n["name"] for n in d.get("networks", []) if n.get("name")],
        "last_air_date": d.get("last_air_date"),
        "in_production": bool(d.get("in_production")),
        "seasons": [
            {
                "season_number": s.get("season_number"),
                "name": s.get("name"),
                "episode_count": s.get("episode_count") or 0,
                "air_date": s.get("air_date"),
                "poster_path": s.get("poster_path"),
            }
            for s in d.get("seasons", [])
            if s.get("season_number") is not None
        ],
    })
    return card
