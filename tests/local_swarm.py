"""A tiny private BitTorrent swarm on localhost, so the built-in client can be tested
end to end with no internet, tracker account, or real content:

  * generates a few sample "releases" (random-byte .mkv files) and .torrent files for them
  * seeds them from a libtorrent session on 127.0.0.1:6891
  * runs a minimal HTTP tracker (/announce) that always answers "the seeder is at
    127.0.0.1:6891", which is what the .torrent files point at
  * serves the .torrent files at /download/<n>.torrent, and /magnet/<n> 302-redirects
    to a magnet link -- the two shapes indexer download links come in

tests/mock_torznab.py's search results link to these. Run with:

    python -m uvicorn tests.local_swarm:app --port 8083
"""

import os
import tempfile
import threading
from pathlib import Path
from urllib.parse import parse_qs, quote

import libtorrent as lt
from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse

SEED_PORT = 6891
HTTP_PORT = 8083
TRACKER_URL = f"http://127.0.0.1:{HTTP_PORT}/announce"

RELEASES = [
    ("Sample.Movie.2024.1080p.BluRay.x264-GROUP.mkv", 8 * 1024 * 1024),
    ("Sample.Movie.2024.720p.WEB-DL.x264-GROUP.mkv", 4 * 1024 * 1024),
    ("Sample.Show.S01E01.1080p.WEB.x264-GROUP.mkv", 6 * 1024 * 1024),
]

root = Path(os.environ.get("SWARM_DIR", Path(tempfile.gettempdir()) / "the-den-swarm"))
seed_dir = root / "seed"
seed_dir.mkdir(parents=True, exist_ok=True)

_cat = lt.alert.category_t
session = lt.session({
    "listen_interfaces": f"127.0.0.1:{SEED_PORT}",
    "enable_dht": False, "enable_lsd": False, "enable_upnp": False, "enable_natpmp": False,
    "user_agent": "The Den local swarm",
    # Every peer in a loopback swarm is 127.0.0.1; the default of one peer per IP
    # would make the first connection from that address shadow all the others.
    "allow_multiple_connections_per_ip": True,
    "alert_mask": _cat.error_notification | _cat.peer_notification | _cat.connect_notification | _cat.status_notification,
})


def _log_alerts() -> None:
    """Print what the seeder sees (connections, handshakes, errors) so a client that
    can't download from it can be debugged from this side too."""
    while True:
        session.wait_for_alert(1000)
        for alert in session.pop_alerts():
            name = type(alert).__name__
            if name in ("state_update_alert", "session_stats_alert"):
                continue
            print(f"[seeder] {name}: {alert.message()}", flush=True)


threading.Thread(target=_log_alerts, daemon=True).start()

torrents: dict[int, bytes] = {}  # n -> .torrent bytes
magnets: dict[int, str] = {}

for n, (name, size) in enumerate(RELEASES, start=1):
    payload = seed_dir / name
    if not payload.exists() or payload.stat().st_size != size:
        payload.write_bytes(os.urandom(size))
    fs = lt.file_storage()
    lt.add_files(fs, str(payload))
    ct = lt.create_torrent(fs)
    ct.add_tracker(TRACKER_URL)
    lt.set_piece_hashes(ct, str(seed_dir))
    data = lt.bencode(ct.generate())
    torrents[n] = data
    ti = lt.torrent_info(data)
    magnets[n] = f"magnet:?xt=urn:btih:{ti.info_hashes().v1}&dn={quote(name)}&tr={quote(TRACKER_URL)}"
    params = lt.add_torrent_params()
    params.ti = ti
    params.save_path = str(seed_dir)
    params.flags |= lt.torrent_flags.seed_mode
    session.add_torrent(params)
    print(f"seeding #{n}: {name} ({size} bytes) infohash {ti.info_hashes().v1}")

app = FastAPI()


handles_by_hash: dict[bytes, lt.torrent_handle] = {
    bytes.fromhex(str(h.info_hashes().v1)): h for h in session.get_torrents()
}


@app.get("/announce")
def announce(request: Request):
    # A real tracker would track who announced; here everyone just gets the seeder.
    # Compact form (4-byte IP + 2-byte port) carries no peer id, so the client can't
    # reject the seeder for handshaking with an id the tracker didn't predict.
    # info_hash is raw bytes, so parse the query string ourselves rather than as text.
    query = parse_qs(request.scope.get("query_string", b""), keep_blank_values=True)
    info_hash = query.get(b"info_hash", [b""])[0]
    port = int(query.get(b"port", [b"0"])[0] or 0)
    if port == SEED_PORT:
        # The seeder announcing itself: don't hand it its own address to connect to.
        return Response(content=lt.bencode({b"interval": 60, b"peers": b""}), media_type="text/plain")

    compact_peer = bytes([127, 0, 0, 1]) + SEED_PORT.to_bytes(2, "big")
    body = lt.bencode({b"interval": 60, b"peers": compact_peer})

    # Also have the seeder dial the announcing client, like an active swarm peer would,
    # so the client's incoming-connection path is exercised as well as its outgoing one.
    handle = handles_by_hash.get(info_hash)
    if handle is not None and port:
        handle.connect_peer((request.client.host, port))
    return Response(content=body, media_type="text/plain")


@app.get("/download/{n}.torrent")
def download(n: int):
    if n not in torrents:
        return Response(status_code=404)
    return Response(content=torrents[n], media_type="application/x-bittorrent")


@app.get("/magnet/{n}")
def magnet(n: int):
    if n not in magnets:
        return Response(status_code=404)
    return RedirectResponse(magnets[n], status_code=302)


@app.get("/status")
def status():
    return [
        {"name": h.status().name, "seeding": h.status().is_seeding, "peers": h.status().num_peers}
        for h in session.get_torrents()
    ]
