"""OpenSubtitles REST API v1 client (E6): search and download subtitles by TMDB id.
Anonymous requests work on the free tier with a lower daily quota -- only an API key is
needed (no OAuth), the same shape as app/tmdb.py's api_key-per-call pattern."""

from __future__ import annotations

from typing import Any

import httpx

BASE_URL = "https://api.opensubtitles.com/api/v1"
USER_AGENT = "TheDen v1"


def _headers(api_key: str) -> dict:
    return {"Api-Key": api_key, "User-Agent": USER_AGENT, "Content-Type": "application/json"}


async def search(api_key: str, tmdb_id: int, languages: list[str], season_number: int | None = None, episode_number: int | None = None) -> list[dict]:
    """Candidate subtitles for a movie or episode, best (most downloaded) first."""
    params: dict[str, Any] = {"tmdb_id": tmdb_id, "languages": ",".join(languages)}
    if season_number is not None:
        params["season_number"] = season_number
    if episode_number is not None:
        params["episode_number"] = episode_number
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/subtitles", params=params, headers=_headers(api_key))
        resp.raise_for_status()
        data = resp.json()
    out = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        files = attrs.get("files", [])
        if not files:
            continue
        out.append({
            "file_id": files[0].get("file_id"),
            "language": attrs.get("language"),
            "release": attrs.get("release"),
            "download_count": attrs.get("download_count", 0),
        })
    out.sort(key=lambda s: s["download_count"], reverse=True)
    return out


async def download(api_key: str, file_id: int) -> str:
    """The subtitle file's text content for one search result's file_id."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{BASE_URL}/download", json={"file_id": file_id}, headers=_headers(api_key))
        resp.raise_for_status()
        link = resp.json().get("link")
        if not link:
            raise ValueError("OpenSubtitles didn't return a download link")
        file_resp = await client.get(link)
        file_resp.raise_for_status()
        return file_resp.text
