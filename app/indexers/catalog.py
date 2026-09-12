"""Indexer presets: pick one, add credentials if it needs any, done.

Three kinds:
- native   -- public trackers The Den talks to directly (app/indexers/native.py); no account.
- newznab  -- usenet indexers; all speak the same API, only the URL and API key differ.
- torznab  -- generic Torznab: a tracker's own API, or a Jackett / Prowlarr instance.
"""

from dataclasses import asdict, dataclass, field

from app.indexers.native import NATIVES


@dataclass(frozen=True)
class Preset:
    slug: str
    name: str
    kind: str            # public | usenet | generic
    implementation: str  # torznab | newznab | <native slug>
    url: str
    description: str
    needs_api_key: bool = False
    cloudflare: bool = False
    site: str = ""
    fields: list[str] = field(default_factory=list)  # which form fields to show: url, api_key


def _native(n) -> Preset:
    return Preset(slug=n.slug, name=n.name, kind="public", implementation=n.slug, url=n.url, description=n.description,
                  cloudflare=n.cloudflare, site=n.url, fields=["url"])


def _usenet(slug, name, url, site, description="Usenet indexer (Newznab). Needs the API key from your account page.") -> Preset:
    return Preset(slug=slug, name=name, kind="usenet", implementation="newznab", url=url, description=description,
                  needs_api_key=True, site=site, fields=["url", "api_key"])


PRESETS: list[Preset] = [
    *[_native(n) for n in NATIVES.values()],
    _usenet("nzbgeek", "NZBgeek", "https://api.nzbgeek.info/api", "https://nzbgeek.info"),
    _usenet("nzbfinder", "NZBFinder", "https://nzbfinder.ws/api", "https://nzbfinder.ws"),
    _usenet("drunkenslug", "DrunkenSlug", "https://api.drunkenslug.com/api", "https://drunkenslug.com"),
    _usenet("nzbplanet", "NZBPlanet", "https://api.nzbplanet.net/api", "https://nzbplanet.net"),
    _usenet("nzbsu", "nzb.su", "https://api.nzb.su/api", "https://nzb.su"),
    _usenet("dognzb", "DOGnzb", "https://api.dognzb.cr/api", "https://dognzb.cr"),
    _usenet("nzbcat", "NZBCat", "https://nzb.cat/api", "https://nzb.cat"),
    _usenet("althub", "altHUB", "https://api.althub.co.za/api", "https://althub.co.za"),
    _usenet("ninjacentral", "NinjaCentral", "https://ninjacentral.co.za/api", "https://ninjacentral.co.za"),
    _usenet("tabularasa", "Tabula Rasa", "https://www.tabula-rasa.pw/api/v1/api", "https://www.tabula-rasa.pw"),
    _usenet("abnzb", "abNZB", "https://abnzb.com/api", "https://abnzb.com"),
    _usenet("nzbndx", "NZBNDX", "https://www.nzbndx.com/api", "https://www.nzbndx.com"),
    _usenet("usenetcrawler", "Usenet Crawler", "https://www.usenet-crawler.com/api", "https://www.usenet-crawler.com"),
    Preset("animetosho", "AnimeTosho", "public", "torznab", "https://feed.animetosho.org/nabapi", "Anime. Native Torznab feed, no account.",
           site="https://animetosho.org", fields=["url"]),
    Preset("jackett", "Jackett", "generic", "torznab", "http://127.0.0.1:9117/api/v2.0/indexers/all/results/torznab/",
           "A Jackett instance: its aggregate Torznab feed plus the API key from its dashboard.", needs_api_key=True, site="https://github.com/Jackett/Jackett", fields=["url", "api_key"]),
    Preset("prowlarr", "Prowlarr", "generic", "torznab", "http://127.0.0.1:9696/1/api",
           "A Prowlarr instance: one of its indexers' Torznab URLs plus Prowlarr's API key.", needs_api_key=True, site="https://prowlarr.com", fields=["url", "api_key"]),
    Preset("torznab", "Custom Torznab", "generic", "torznab", "", "Any tracker or proxy that speaks Torznab.", fields=["url", "api_key"]),
    Preset("newznab", "Custom Newznab", "generic", "newznab", "", "Any usenet indexer that speaks Newznab.", needs_api_key=True, fields=["url", "api_key"]),
]

BY_SLUG: dict[str, Preset] = {p.slug: p for p in PRESETS}


def as_dicts() -> list[dict]:
    return [asdict(p) for p in PRESETS]
