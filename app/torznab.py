"""Client for the Torznab/Newznab protocol: RSS/XML search API most indexers speak.

Endpoints look like: GET {base_url}?t=caps&apikey=KEY
                      GET {base_url}?t=search&q=QUERY&apikey=KEY
Results come back as an RSS feed where each <item> carries extra metadata
(size, seeders, peers) as <torznab:attr name="..." value="..."/> children.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx


@dataclass
class Release:
    title: str
    download_url: str
    indexer_name: str
    size: int | None = None
    seeders: int | None = None
    peers: int | None = None


def _attr_map(item: ET.Element) -> dict[str, str]:
    """Collect torznab:attr/newznab:attr children regardless of namespace prefix."""
    attrs = {}
    for el in item:
        tag = el.tag.rsplit("}", 1)[-1]  # strip {namespace} prefix
        if tag == "attr" and "name" in el.attrib:
            attrs[el.attrib["name"]] = el.attrib.get("value")
    return attrs


def _parse_items(xml_bytes: bytes, indexer_name: str) -> list[Release]:
    root = ET.fromstring(xml_bytes)
    releases = []
    for item in root.iter("item"):
        title = item.findtext("title") or "(no title)"
        enclosure = item.find("enclosure")
        download_url = enclosure.attrib["url"] if enclosure is not None else (item.findtext("link") or "")
        attrs = _attr_map(item)
        releases.append(
            Release(
                title=title,
                download_url=download_url,
                indexer_name=indexer_name,
                size=int(attrs["size"]) if attrs.get("size", "").isdigit() else None,
                seeders=int(attrs["seeders"]) if attrs.get("seeders", "").isdigit() else None,
                peers=int(attrs["peers"]) if attrs.get("peers", "").isdigit() else None,
            )
        )
    return releases


async def test_connection(url: str, api_key: str | None) -> dict:
    """Hit t=caps to confirm the URL/API key are valid. Returns caps info or raises."""
    params = {"t": "caps"}
    if api_key:
        params["apikey"] = api_key
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        server = root.find("server")
        return {"ok": True, "server_title": server.attrib.get("title") if server is not None else None}


async def search(url: str, api_key: str | None, query: str, indexer_name: str) -> list[Release]:
    params = {"t": "search", "q": query}
    if api_key:
        params["apikey"] = api_key
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return _parse_items(resp.content, indexer_name)
