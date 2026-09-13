"""SABnzbd integration (E7): The Den doesn't run its own usenet downloader -- it
sends NZBs to an existing SABnzbd instance the same way it treats FlareSolverr, an
external service configured with a URL (here, plus an API key)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class SabFile:
    path: str  # absolute
    size: int
    downloaded: int


async def _call(base_url: str, api_key: str, mode: str, params: dict | None = None) -> dict:
    url = f"{base_url.rstrip('/')}/api"
    query = {"mode": mode, "apikey": api_key, "output": "json", **(params or {})}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, params=query)
        resp.raise_for_status()
        return resp.json()


async def test_connection(base_url: str, api_key: str) -> dict:
    """Hit the version endpoint to confirm the URL/API key are valid."""
    return await _call(base_url, api_key, "version")


async def add(base_url: str, api_key: str, nzb_url: str, name: str) -> str:
    """Send an NZB by URL to SABnzbd's queue. Returns its nzo_id."""
    data = await _call(base_url, api_key, "addurl", {"name": nzb_url, "nzbname": name})
    nzo_ids = data.get("nzo_ids") or []
    if not data.get("status") or not nzo_ids:
        raise ValueError(f"SABnzbd rejected the NZB: {data}")
    return nzo_ids[0]


def _queue_status(item: dict, nzo_id: str) -> dict:
    mb, mbleft = float(item.get("mb") or 0), float(item.get("mbleft") or 0)
    total = mb * 1048576
    downloaded = total - mbleft * 1048576
    return {
        "key": nzo_id, "name": item.get("filename") or "", "state": (item.get("status") or "queued").lower(),
        "progress": (downloaded / total) if total else 0.0, "total_size": int(total), "downloaded": int(max(downloaded, 0)),
        "is_finished": False, "error": None, "save_path": None,
    }


def _history_status(item: dict, nzo_id: str) -> dict:
    failed = (item.get("status") or "").lower() == "failed"
    size = int(item.get("bytes") or 0)
    return {
        "key": nzo_id, "name": item.get("name") or "", "state": "error" if failed else "done",
        "progress": 1.0, "total_size": size, "downloaded": size,
        "is_finished": not failed, "error": item.get("fail_message") or None, "save_path": item.get("storage") or None,
    }


async def status(base_url: str, api_key: str, nzo_id: str) -> dict | None:
    """A queue or history entry normalized close to app.torrent.engine.TorrentStatus's
    shape (only the fields download_check.py actually reads)."""
    queue = await _call(base_url, api_key, "queue")
    for item in (queue.get("queue", {}).get("slots") or []):
        if item.get("nzo_id") == nzo_id:
            return _queue_status(item, nzo_id)
    history = await _call(base_url, api_key, "history")
    for item in (history.get("history", {}).get("slots") or []):
        if item.get("nzo_id") == nzo_id:
            return _history_status(item, nzo_id)
    return None


async def files(base_url: str, api_key: str, nzo_id: str) -> list[SabFile]:
    """The finished job's files, straight off disk in SABnzbd's own completed-job
    folder (SABnzbd already repaired/extracted it) -- the download_check.py import
    path treats this the same as a torrent's file list."""
    st = await status(base_url, api_key, nzo_id)
    if not st or not st.get("save_path") or not st["is_finished"]:
        return []
    root = Path(st["save_path"])
    if not root.exists():
        return []
    out = []
    for path in root.rglob("*"):
        if path.is_file():
            size = path.stat().st_size
            out.append(SabFile(path=str(path), size=size, downloaded=size))
    return out


async def remove(base_url: str, api_key: str, nzo_id: str, delete_files: bool = True) -> None:
    """Remove from the queue or history (wherever it is); ignore "not found"."""
    for mode, params in (
        ("queue", {"name": "delete", "value": nzo_id, "del_files": int(delete_files)}),
        ("history", {"name": "delete", "value": nzo_id, "del_files": int(delete_files)}),
    ):
        try:
            await _call(base_url, api_key, mode, params)
        except Exception:
            pass
