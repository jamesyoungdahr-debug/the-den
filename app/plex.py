"""Plex: the plex.tv account API (PIN sign-in, account, servers, shared users) and the
bits of a Plex Media Server we need (library sections). Everything Plex-shaped lives here
so a change on Plex's side is a one-file fix.

The sign-in flow (documented by Plex on its forums, used by every third-party app):
  1. POST /api/v2/pins?strong=true            -> {id, code}
  2. send the user to https://app.plex.tv/auth#?clientID=..&code=..&forwardUrl=..
  3. GET  /api/v2/pins/{id}?code=..           -> {authToken} once they've signed in
  4. GET  /api/v2/user  (X-Plex-Token)        -> the account
Every request carries X-Plex-Client-Identifier, a UUID this install generates once and
keeps under STATE_DIR -- Plex ties the PIN and the resulting token to it.

PLEX_TV_URL / PLEX_AUTH_URL exist only so tests/mock_plex.py can stand in for plex.tv.
"""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

import httpx

from app import config

PRODUCT = "The Den"
VERSION = "0.2"


def client_identifier() -> str:
    path = Path(config.STATE_DIR) / "plex_client_id"
    try:
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    value = str(uuid.uuid4())
    path.write_text(value, encoding="utf-8")
    return value


def _headers(token: str | None = None, accept: str = "application/json") -> dict:
    headers = {
        "Accept": accept,
        "X-Plex-Product": PRODUCT,
        "X-Plex-Version": VERSION,
        "X-Plex-Client-Identifier": client_identifier(),
        "X-Plex-Platform": "Web",
        "X-Plex-Device": PRODUCT,
        "X-Plex-Device-Name": PRODUCT,
    }
    if token:
        headers["X-Plex-Token"] = token
    return headers


@dataclass
class Pin:
    id: int
    code: str


@dataclass
class Account:
    id: int
    uuid: str
    username: str
    email: str | None
    thumb: str | None


@dataclass
class Server:
    name: str
    machine_id: str
    uri: str  # best connection: local first, then remote
    owned: bool


class PlexError(Exception):
    pass


# ---- sign-in ---------------------------------------------------------------------

async def create_pin() -> Pin:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{config.PLEX_TV_URL}/api/v2/pins", data={"strong": "true"}, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
    return Pin(id=int(data["id"]), code=str(data["code"]))


def auth_url(code: str, forward_url: str | None) -> str:
    params = {"clientID": client_identifier(), "code": code, "context[device][product]": PRODUCT}
    if forward_url:
        params["forwardUrl"] = forward_url
    return f"{config.PLEX_AUTH_URL}#?{urlencode(params)}"


async def check_pin(pin_id: int, code: str) -> str | None:
    """The auth token once the user has signed in on plex.tv, else None (not yet / expired)."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{config.PLEX_TV_URL}/api/v2/pins/{pin_id}", params={"code": code}, headers=_headers())
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        token = resp.json().get("authToken")
    return token or None


async def get_account(token: str) -> Account:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{config.PLEX_TV_URL}/api/v2/user", headers=_headers(token))
        if resp.status_code == 401:
            raise PlexError("Plex rejected that token")
        resp.raise_for_status()
        data = resp.json()
    return Account(
        id=int(data["id"]), uuid=str(data.get("uuid") or ""), username=str(data.get("username") or data.get("title") or f"plex-{data['id']}"),
        email=data.get("email") or None, thumb=data.get("thumb") or None,
    )


# ---- servers and access ----------------------------------------------------------

async def list_servers(token: str) -> list[Server]:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{config.PLEX_TV_URL}/api/v2/resources", params={"includeHttps": "1", "includeRelay": "0"}, headers=_headers(token)
        )
        resp.raise_for_status()
        resources = resp.json()
    servers = []
    for r in resources:
        if "server" not in str(r.get("provides", "")):
            continue
        conns = r.get("connections") or []
        local = [c for c in conns if c.get("local")]
        remote = [c for c in conns if not c.get("local")]
        chosen = (local or remote or [{}])[0]
        uri = chosen.get("uri") or ""
        if not uri:
            continue
        servers.append(Server(name=r.get("name") or "Plex", machine_id=r.get("clientIdentifier") or "", uri=uri.rstrip("/"), owned=bool(r.get("owned"))))
    return servers


async def shared_user_ids(owner_token: str, machine_id: str) -> set[int]:
    """Plex account ids the owner shares `machine_id` with. Older XML endpoint (as used by
    Overseerr); there is no JSON equivalent for shares."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{config.PLEX_TV_URL}/api/users", headers=_headers(owner_token, accept="application/xml"))
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    ids: set[int] = set()
    for user in root.iter("User"):
        for server in user.iter("Server"):
            if server.attrib.get("machineIdentifier") == machine_id:
                try:
                    ids.add(int(user.attrib["id"]))
                except (KeyError, ValueError):
                    pass
    return ids


async def library_sections(server_uri: str, token: str) -> list[dict]:
    """The libraries on a Plex Media Server: [{key, title, type}] with type movie|show|..."""
    async with httpx.AsyncClient(timeout=20, verify=False) as client:
        resp = await client.get(f"{server_uri}/library/sections", headers=_headers(token))
        resp.raise_for_status()
        data = resp.json()
    out = []
    for d in data.get("MediaContainer", {}).get("Directory", []):
        out.append({"key": str(d.get("key")), "title": d.get("title"), "type": d.get("type")})
    return out
