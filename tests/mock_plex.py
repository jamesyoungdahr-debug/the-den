"""Stand-in for plex.tv AND a Plex Media Server, so the Plex sign-in flow, the shared-user
check, server/section discovery, and (later) the library scan all run offline.

Run:   python -m uvicorn tests.mock_plex:app --port 8084
Point the app at it with PLEX_TV_URL=http://127.0.0.1:8084 PLEX_AUTH_URL=http://127.0.0.1:8084/auth

Three fake Plex accounts exist:
  owner    (id 1000) owns the server "Mock Plex" (machine id MOCK-MACHINE-1)
  friend   (id 2000) is shared that server
  stranger (id 3000) has a Plex account but no access
The /auth page (what app.plex.tv would be) lets you pick who signs in, then forwards back.
Tests can also claim a PIN directly: POST /_mock/claim/{pin_id}?as=friend
"""

from fastapi import FastAPI, Header, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

ACCOUNTS = {
    "owner": {"id": 1000, "uuid": "u-owner", "username": "plexowner", "email": "owner@example.invalid", "thumb": "https://plex.tv/users/owner/avatar", "token": "tok-owner"},
    "friend": {"id": 2000, "uuid": "u-friend", "username": "plexfriend", "email": "friend@example.invalid", "thumb": None, "token": "tok-friend"},
    "stranger": {"id": 3000, "uuid": "u-stranger", "username": "plexstranger", "email": None, "thumb": None, "token": "tok-stranger"},
}
MACHINE_ID = "MOCK-MACHINE-1"

_pins: dict[int, dict] = {}
_next_pin = [7000]


def _account_for_token(token: str | None) -> dict | None:
    return next((a for a in ACCOUNTS.values() if a["token"] == token), None)


# ---- plex.tv ---------------------------------------------------------------------

@app.post("/api/v2/pins")
def create_pin():
    _next_pin[0] += 1
    pin = {"id": _next_pin[0], "code": f"CODE{_next_pin[0]}", "authToken": None}
    _pins[pin["id"]] = pin
    return pin


@app.get("/api/v2/pins/{pin_id}")
def check_pin(pin_id: int, code: str = ""):
    pin = _pins.get(pin_id)
    if pin is None or pin["code"] != code:
        return Response(status_code=404)
    return pin


@app.post("/_mock/claim/{pin_id}")
def claim_pin(pin_id: int, **_):
    return Response(status_code=404)


@app.post("/_mock/claim/{pin_id}/{who}")
def claim_pin_as(pin_id: int, who: str):
    pin = _pins.get(pin_id)
    if pin is None or who not in ACCOUNTS:
        return Response(status_code=404)
    pin["authToken"] = ACCOUNTS[who]["token"]
    return {"ok": True}


@app.get("/auth", response_class=HTMLResponse)
def auth_page(request: Request):
    """app.plex.tv puts its parameters in the URL fragment, which servers never see; this
    page reads them client-side, offers a choice of account, claims the PIN, and forwards."""
    return """<!doctype html><meta charset="utf-8"><title>Mock plex.tv</title>
<body style="font-family:sans-serif;background:#111;color:#eee;padding:40px">
<h2>Mock plex.tv — who is signing in?</h2>
<p id="info"></p>
<button onclick="go('owner')">owner</button> <button onclick="go('friend')">friend</button> <button onclick="go('stranger')">stranger</button>
<script>
const p = new URLSearchParams(location.hash.slice(2));
document.getElementById('info').textContent = 'clientID=' + p.get('clientID') + ' code=' + p.get('code');
async function go(who){
  const code = p.get('code');
  const pins = await fetch('/_mock/pins').then(r => r.json());
  const pin = pins.find(x => x.code === code);
  await fetch('/_mock/claim/' + pin.id + '/' + who, {method:'POST'});
  location.href = p.get('forwardUrl');
}
</script></body>"""


@app.get("/_mock/pins")
def list_pins():
    return list(_pins.values())


@app.get("/api/v2/user")
def get_user(x_plex_token: str | None = Header(default=None)):
    account = _account_for_token(x_plex_token)
    if account is None:
        return Response(status_code=401)
    return {k: v for k, v in account.items() if k != "token"}


@app.get("/api/v2/resources")
def resources(x_plex_token: str | None = Header(default=None)):
    account = _account_for_token(x_plex_token)
    if account is None:
        return Response(status_code=401)
    if account["id"] == ACCOUNTS["stranger"]["id"]:
        return []
    return [{
        "name": "Mock Plex", "clientIdentifier": MACHINE_ID, "provides": "server",
        "owned": account["id"] == ACCOUNTS["owner"]["id"],
        "connections": [
            {"uri": "http://127.0.0.1:8084", "local": True, "protocol": "http"},
            {"uri": "https://mock.plex.direct:32400", "local": False, "protocol": "https"},
        ],
    }]


@app.get("/api/users")
def shared_users(x_plex_token: str | None = Header(default=None)):
    account = _account_for_token(x_plex_token)
    if account is None or account["id"] != ACCOUNTS["owner"]["id"]:
        return Response(status_code=401)
    friend = ACCOUNTS["friend"]
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<MediaContainer friendlyName="myPlex" size="1">
  <User id="{friend['id']}" title="{friend['username']}" username="{friend['username']}" email="{friend['email']}">
    <Server id="1" serverId="1" machineIdentifier="{MACHINE_ID}" name="Mock Plex" owned="0"/>
  </User>
</MediaContainer>"""
    return Response(content=xml, media_type="application/xml")


# ---- Plex Media Server -----------------------------------------------------------

@app.get("/library/sections")
def library_sections(x_plex_token: str | None = Header(default=None)):
    if _account_for_token(x_plex_token) is None:
        return Response(status_code=401)
    return {"MediaContainer": {"Directory": [
        {"key": "1", "title": "Movies", "type": "movie"},
        {"key": "2", "title": "TV Shows", "type": "show"},
        {"key": "3", "title": "Music", "type": "artist"},
    ]}}


# The library: real TMDB ids so the scan lines up with live Discover pages.
#   Dune: Part Two (tmdb 693134) and Inception (27205, legacy agent guid) in Movies;
#   Severance (tmdb 95396, tvdb 371980) with season 1 complete in TV Shows.
LIBRARY = {
    "1": [
        {"ratingKey": "101", "type": "movie", "title": "Dune: Part Two", "year": 2024, "thumb": "/library/metadata/101/thumb/1",
         "Guid": [{"id": "tmdb://693134"}, {"id": "imdb://tt15239678"}]},
        {"ratingKey": "102", "type": "movie", "title": "Inception", "year": 2010, "thumb": "/library/metadata/102/thumb/1",
         "guid": "com.plexapp.agents.themoviedb://27205?lang=en"},
    ],
    "2": [
        {"ratingKey": "201", "type": "show", "title": "Severance", "year": 2022, "thumb": "/library/metadata/201/thumb/1",
         "Guid": [{"id": "tmdb://95396"}, {"id": "tvdb://371980"}, {"id": "imdb://tt11280740"}]},
    ],
}


def _png(width: int = 2, height: int = 3, rgb: tuple[int, int, int] = (0xB1, 0x4D, 0xFF)) -> bytes:
    """A tiny solid-colour PNG (real CRCs, real zlib) standing in for every poster."""
    import struct
    import zlib

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


THUMB_PNG = _png()
SEASONS = {"201": [{"type": "season", "index": 1, "leafCount": 9}]}


@app.get("/library/sections/{key}/all")
def section_items(key: str, x_plex_token: str | None = Header(default=None), x_plex_container_start: int = Header(default=0),
                  x_plex_container_size: int = Header(default=100)):
    if _account_for_token(x_plex_token) is None:
        return Response(status_code=401)
    items = LIBRARY.get(key, [])
    page = items[x_plex_container_start:x_plex_container_start + x_plex_container_size]
    return {"MediaContainer": {"totalSize": len(items), "size": len(page), "Metadata": page}}


@app.get("/library/metadata/{rating_key}/thumb/{version}")
def thumb(rating_key: str, version: str, x_plex_token: str | None = Header(default=None)):
    if _account_for_token(x_plex_token) is None:
        return Response(status_code=401)
    return Response(content=THUMB_PNG, media_type="image/png")


@app.get("/library/metadata/{rating_key}/children")
def children(rating_key: str, x_plex_token: str | None = Header(default=None)):
    if _account_for_token(x_plex_token) is None:
        return Response(status_code=401)
    return {"MediaContainer": {"Metadata": SEASONS.get(rating_key, [])}}


@app.get("/")
def root():
    return RedirectResponse("/auth")
