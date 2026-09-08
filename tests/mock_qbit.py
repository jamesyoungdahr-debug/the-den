"""Stand-in for qBittorrent's WebUI API. Simulates an instantly-finished download
so we can test the grab -> check -> import loop without waiting on a real transfer."""

import tempfile
from pathlib import Path

from fastapi import FastAPI, Form, Response

app = FastAPI()

_torrents: dict[str, dict] = {}  # category -> torrent info
_downloads_dir = Path(tempfile.gettempdir()) / "the-den-mock-downloads"
_downloads_dir.mkdir(exist_ok=True)


@app.post("/api/v2/auth/login")
def login():
    return Response("Ok.")


@app.post("/api/v2/torrents/add")
def add_torrent(urls: str = Form(...), category: str = Form(...)):
    content_dir = _downloads_dir / category
    content_dir.mkdir(exist_ok=True)
    fake_video = content_dir / "movie.mkv"
    fake_video.write_bytes(b"0" * 1024)  # dummy file, just needs to exist with a video extension

    _torrents[category] = {
        "hash": category,
        "name": urls,
        "progress": 1.0,  # pretend it's done immediately
        "state": "uploading",
        "content_path": str(fake_video),
        "save_path": str(content_dir),
    }
    return Response("Ok.")


@app.get("/api/v2/torrents/info")
def torrents_info(category: str = ""):
    torrent = _torrents.get(category)
    return [torrent] if torrent else []
