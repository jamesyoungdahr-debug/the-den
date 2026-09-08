import httpx

from app import config


async def search_movie(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{config.TMDB_BASE_URL}/search/movie",
            params={"api_key": config.TMDB_API_KEY, "query": query},
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("results", []):
        release_date = item.get("release_date") or ""
        results.append(
            {
                "tmdb_id": item["id"],
                "title": item["title"],
                "year": int(release_date[:4]) if release_date[:4].isdigit() else None,
                "overview": item.get("overview"),
                "poster_path": item.get("poster_path"),
            }
        )
    return results


async def search_tv(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{config.TMDB_BASE_URL}/search/tv",
            params={"api_key": config.TMDB_API_KEY, "query": query},
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("results", []):
        first_air = item.get("first_air_date") or ""
        results.append(
            {
                "tmdb_id": item["id"],
                "title": item["name"],
                "year": int(first_air[:4]) if first_air[:4].isdigit() else None,
                "overview": item.get("overview"),
                "poster_path": item.get("poster_path"),
            }
        )
    return results


async def get_tv_episodes(tmdb_id: int) -> list[dict]:
    """Fetch every episode of every season for a series (a handful of requests)."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{config.TMDB_BASE_URL}/tv/{tmdb_id}", params={"api_key": config.TMDB_API_KEY})
        resp.raise_for_status()
        show = resp.json()

        episodes = []
        for season in show.get("seasons", []):
            season_number = season["season_number"]
            if season_number == 0:
                continue  # skip "specials"
            resp = await client.get(
                f"{config.TMDB_BASE_URL}/tv/{tmdb_id}/season/{season_number}",
                params={"api_key": config.TMDB_API_KEY},
            )
            resp.raise_for_status()
            for ep in resp.json().get("episodes", []):
                episodes.append(
                    {
                        "season_number": season_number,
                        "episode_number": ep["episode_number"],
                        "title": ep.get("name"),
                        "air_date": ep.get("air_date"),
                    }
                )
        return episodes
