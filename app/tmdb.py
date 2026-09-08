import httpx

from app import config


async def search_movie(query: str, api_key: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{config.TMDB_BASE_URL}/search/movie",
            params={"api_key": api_key, "query": query},
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
