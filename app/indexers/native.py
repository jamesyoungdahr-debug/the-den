"""Native indexers: public trackers that have no Torznab API, talked to directly.

Each implementation is a small class with a `slug`, a default `url`, whether the site
sits behind Cloudflare, and `search(fetcher, base_url, query)` returning the same
`Release` records the Torznab client produces, so scoring, grabbing and the UI never
know the difference. Magnet links are preferred (the built-in engine adds them without
a second request); where a site only exposes an info-hash we build the magnet.
"""

import asyncio
import html
import re
import urllib.parse
import xml.etree.ElementTree as ET

from app.indexers.fetch import Fetcher
from app.torznab import Release

# Well-known open trackers appended to built magnets so the engine finds peers quickly.
_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
]
_UNITS = {"b": 1, "kb": 1024, "kib": 1024, "mb": 1024**2, "mib": 1024**2, "gb": 1024**3, "gib": 1024**3, "tb": 1024**4, "tib": 1024**4}


def magnet(info_hash: str, name: str) -> str:
    q = urllib.parse.urlencode({"dn": name}) + "".join(f"&tr={urllib.parse.quote(t, safe='')}" for t in _TRACKERS)
    return f"magnet:?xt=urn:btih:{info_hash.lower()}&{q}"


def parse_size(text: str | None) -> int | None:
    """'1.4 GB', '700 MiB', '1,234 KB' -> bytes."""
    if not text:
        return None
    m = re.search(r"([\d.,]+)\s*([KMGT]i?B|B)", text, re.I)
    if not m:
        return None
    try:
        return int(float(m.group(1).replace(",", "")) * _UNITS[m.group(2).lower()])
    except (ValueError, KeyError):
        return None


def _rss(xml: str) -> ET.Element:
    """Parse an RSS body, dropping anything after </rss>: Cloudflare appends a <script>
    block to some sites' feeds, which is "junk after document element" to the parser."""
    end = xml.rfind("</rss>")
    if end != -1:
        xml = xml[: end + len("</rss>")]
    return ET.fromstring(xml.strip().encode())


def _int(v) -> int | None:
    try:
        return int(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _text(el: ET.Element | None, name: str) -> str | None:
    """findtext ignoring namespace prefixes (nyaa:seeders, torznab:attr...)."""
    if el is None:
        return None
    for child in el:
        if child.tag.rsplit("}", 1)[-1] == name:
            return child.text
    return None


class Native:
    slug = ""
    name = ""
    url = ""
    cloudflare = False
    description = ""

    async def search(self, fetcher: Fetcher, base_url: str, query: str) -> list[Release]:
        raise NotImplementedError

    async def test(self, fetcher: Fetcher, base_url: str) -> dict:
        releases = await self.search(fetcher, base_url, "2024")
        return {"ok": True, "server_title": self.name, "sample_results": len(releases)}


class PirateBay(Native):
    slug, name, url = "tpb", "The Pirate Bay", "https://apibay.org"
    description = "Public tracker via its JSON API (apibay). No account."

    async def search(self, fetcher, base_url, query):
        rows = await fetcher.get_json(f"{base_url.rstrip('/')}/q.php", {"q": query, "cat": 0}, cloudflare=self.cloudflare)
        out = []
        for r in rows or []:
            if str(r.get("id")) == "0" or not r.get("info_hash"):
                continue  # apibay's "No results returned" placeholder row
            out.append(Release(title=r["name"], download_url=magnet(r["info_hash"], r["name"]), indexer_name=self.name,
                               size=_int(r.get("size")), seeders=_int(r.get("seeders")), peers=_int(r.get("leechers"))))
        return out


class YTS(Native):
    slug, name, url = "yts", "YTS", "https://yts.mx"
    description = "Movies only, small encodes, every quality as a separate release. No account. Some ISPs block yts.mx; use a mirror URL if the test fails on DNS."

    async def search(self, fetcher, base_url, query):
        data = await fetcher.get_json(f"{base_url.rstrip('/')}/api/v2/list_movies.json", {"query_term": query, "limit": 50}, cloudflare=self.cloudflare)
        out = []
        for m in ((data or {}).get("data") or {}).get("movies") or []:
            for t in m.get("torrents") or []:
                title = f"{m.get('title_long') or m.get('title')} [{t.get('quality')}] [{t.get('type')}] [YTS]"
                out.append(Release(title=title, download_url=magnet(t["hash"], title), indexer_name=self.name,
                                   size=_int(t.get("size_bytes")), seeders=_int(t.get("seeds")), peers=_int(t.get("peers"))))
        return out


class Nyaa(Native):
    slug, name, url = "nyaa", "Nyaa", "https://nyaa.si"
    description = "Anime and Asian media. RSS search, no account."

    async def search(self, fetcher, base_url, query):
        xml = await fetcher.get_text(f"{base_url.rstrip('/')}/", {"page": "rss", "q": query, "c": "0_0", "f": "0"}, cloudflare=self.cloudflare)
        out = []
        for item in _rss(xml).iter("item"):
            title = item.findtext("title") or ""
            ih = _text(item, "infoHash")
            link = magnet(ih, title) if ih else (item.findtext("link") or "")
            out.append(Release(title=title, download_url=link, indexer_name=self.name, size=parse_size(_text(item, "size")),
                               seeders=_int(_text(item, "seeders")), peers=_int(_text(item, "leechers"))))
        return out


class Knaben(Native):
    slug, name, url = "knaben", "Knaben", "https://api.knaben.org"
    description = "Meta-search over dozens of public trackers in one call. No account. A good first indexer."

    async def search(self, fetcher, base_url, query):
        body = {"search_type": "score", "search_field": "title", "query": query, "order_by": "seeders", "order_direction": "desc", "size": 100, "hide_unsafe": True, "hide_xxx": True}
        data = await fetcher.post_json(f"{base_url.rstrip('/')}/v1", body)
        out = []
        for h in (data or {}).get("hits") or []:
            link = h.get("magnetUrl") or h.get("link")
            if not link or not h.get("title"):
                continue
            out.append(Release(title=h["title"], download_url=link, indexer_name=f"{self.name} ({h.get('tracker')})" if h.get("tracker") else self.name,
                               size=_int(h.get("bytes")), seeders=_int(h.get("seeders")), peers=_int(h.get("peers"))))
        return out


class LimeTorrents(Native):
    slug, name, url = "limetorrents", "LimeTorrents", "https://www.limetorrents.fun"
    description = "General public tracker. RSS search, no account."

    async def search(self, fetcher, base_url, query):
        xml = await fetcher.get_text(f"{base_url.rstrip('/')}/searchrss/{urllib.parse.quote(query)}/", cloudflare=self.cloudflare)
        out = []
        for item in _rss(xml).iter("item"):
            title = item.findtext("title") or ""
            desc = html.unescape(item.findtext("description") or "")
            enclosure = item.find("enclosure")
            link = enclosure.attrib.get("url") if enclosure is not None else (item.findtext("link") or "")
            seeds = re.search(r"Seeds?:\s*([\d,]+)", desc)
            leech = re.search(r"Leechers?:\s*([\d,]+)", desc)
            size = parse_size(re.search(r"Size:\s*([\d.,]+\s*[KMGT]i?B)", desc).group(1)) if re.search(r"Size:\s*([\d.,]+\s*[KMGT]i?B)", desc) else (_int(enclosure.attrib.get("length")) if enclosure is not None else None)
            out.append(Release(title=title, download_url=link, indexer_name=self.name, size=size,
                               seeders=_int(seeds.group(1)) if seeds else None, peers=_int(leech.group(1)) if leech else None))
        return out


class TorrentDownloads(Native):
    slug, name, url = "torrentdownloads", "TorrentDownloads", "https://www.torrentdownloads.pro"
    description = "General public tracker. RSS search with info-hashes, no account."

    async def search(self, fetcher, base_url, query):
        xml = await fetcher.get_text(f"{base_url.rstrip('/')}/rss.xml", {"type": "search", "search": query}, cloudflare=self.cloudflare)
        out = []
        for item in _rss(xml).iter("item"):
            title = item.findtext("title") or ""
            ih = item.findtext("info_hash")
            if not ih:
                continue
            out.append(Release(title=title, download_url=magnet(ih, title), indexer_name=self.name, size=_int(item.findtext("size")),
                               seeders=_int(item.findtext("seeders")), peers=_int(item.findtext("leechers"))))
        return out


class EZTV(Native):
    slug, name, url = "eztv", "EZTV", "https://eztvx.to"
    description = "TV episodes. Its API cannot search by title, so this reads the site's search page."
    _row = re.compile(r'<a href="(/ep/[^"]+)"[^>]*class="epinfo"[^>]*title="([^"]+)".*?<a href="(magnet:[^"]+)".*?<td[^>]*>([\d.]+\s*[KMGT]B)</td>.*?(?:<font color="green">([\d,]+)</font>|<td[^>]*>-</td>)', re.S)

    async def search(self, fetcher, base_url, query):
        page = await fetcher.get_text(f"{base_url.rstrip('/')}/search/{urllib.parse.quote(query.replace(' ', '-'))}", cloudflare=self.cloudflare)
        out = []
        for _href, title, mag, size, seeds in self._row.findall(page):
            title = html.unescape(re.sub(r"\s*\(.*?\)\s*$", "", title)).strip() or html.unescape(title)
            out.append(Release(title=title, download_url=html.unescape(mag), indexer_name=self.name, size=parse_size(size), seeders=_int(seeds) if seeds else 0, peers=None))
        return out


class X1337(Native):
    slug, name, url, cloudflare = "1337x", "1337x", "https://1337x.to", True
    description = "General public tracker behind Cloudflare: needs FlareSolverr/Byparr. Magnets come from each result's page, so results are capped."
    _row = re.compile(r'<td class="coll-1 name">.*?<a href="(/torrent/[^"]+)">(.*?)</a></td>\s*<td class="coll-2 seeds">([\d,]+)</td>\s*<td class="coll-3 leeches">([\d,]+)</td>.*?<td class="coll-4 size[^"]*">([\d.,]+\s*[KMGT]i?B)', re.S)
    _magnet = re.compile(r'href="(magnet:\?[^"]+)"')
    limit = 15

    async def search(self, fetcher, base_url, query):
        base = base_url.rstrip("/")
        page = await fetcher.get_text(f"{base}/search/{urllib.parse.quote(query)}/1/", cloudflare=self.cloudflare)
        rows = self._row.findall(page)[: self.limit]

        async def resolve(href, title, seeds, leech, size):
            detail = await fetcher.get_text(base + href, cloudflare=self.cloudflare)
            m = self._magnet.search(detail)
            if not m:
                return None
            return Release(title=html.unescape(title), download_url=html.unescape(m.group(1)), indexer_name=self.name,
                           size=parse_size(size), seeders=_int(seeds), peers=_int(leech))

        found = await asyncio.gather(*(resolve(*r) for r in rows), return_exceptions=True)
        return [r for r in found if isinstance(r, Release)]


NATIVES: dict[str, Native] = {n.slug: n for n in (Knaben(), PirateBay(), YTS(), Nyaa(), LimeTorrents(), TorrentDownloads(), EZTV(), X1337())}
