"""Offline checks for app/indexers/native.py: recorded sample responses, so each tracker's
format is pinned without network access. Run: python tests/test_native_indexers.py"""

import asyncio
import sys

sys.path.insert(0, ".")

from app.indexers.native import NATIVES, magnet, parse_size, _rss  # noqa: E402


class FakeFetcher:
    def __init__(self, text: str = "", data=None):
        self.text = text
        self.data = data
        self.calls = []

    async def get_text(self, url, params=None, *, cloudflare=False, headers=None):
        self.calls.append((url, params))
        return self.text

    async def get_json(self, url, params=None, *, cloudflare=False):
        self.calls.append((url, params))
        return self.data

    async def post_json(self, url, body):
        self.calls.append((url, body))
        return self.data


def run(slug: str, fetcher: FakeFetcher, query: str = "test") -> list:
    return asyncio.run(NATIVES[slug].search(fetcher, NATIVES[slug].url, query))


def test_parse_size():
    assert parse_size("1.4 GB") == int(1.4 * 1024**3)
    assert parse_size("700 MiB") == 734003200
    assert parse_size(None) is None
    assert parse_size("abc") is None


def test_magnet():
    m = magnet("ABCDEF", "My Show")
    assert m.startswith("magnet:?xt=urn:btih:abcdef&")
    assert "dn=My+Show" in m
    assert "&tr=" in m


def test_rss_drops_trailing_script():
    root = _rss(
        '<rss><channel><item><title>x</title></item></channel></rss><script>junk</script>'
    )
    assert len(list(root.iter("item"))) == 1


def test_tpb():
    data = [
        {"id": "1", "name": "Ubuntu 24.04", "info_hash": "0123456789ABCDEF0123456789ABCDEF01234567", "seeders": "12", "leechers": "3", "size": "734003200"},
        {"id": "0", "name": "No results returned", "info_hash": "0000000000000000000000000000000000000000", "seeders": "0", "leechers": "0", "size": "0"},
    ]
    rs = run("tpb", FakeFetcher(data=data))
    assert len(rs) == 1
    r = rs[0]
    assert r.title == "Ubuntu 24.04"
    assert r.download_url.startswith("magnet:?xt=urn:btih:0123456789abcdef")
    assert r.seeders == 12
    assert r.peers == 3
    assert r.size == 734003200
    assert r.indexer_name == "The Pirate Bay"


def test_yts():
    data = {
        "data": {
            "movies": [
                {
                    "title_long": "Movie (2020)",
                    "torrents": [
                        {"hash": "ABC", "quality": "1080p", "type": "bluray", "seeds": 5, "peers": 1, "size_bytes": 2000000000},
                        {"hash": "DEF", "quality": "720p", "type": "web", "seeds": 2, "peers": 0, "size_bytes": 900000000},
                    ],
                }
            ]
        }
    }
    rs = run("yts", FakeFetcher(data=data))
    assert len(rs) == 2
    assert rs[0].title == "Movie (2020) [1080p] [bluray] [YTS]"
    assert rs[0].seeders == 5
    assert rs[0].size == 2000000000
    assert "urn:btih:abc" in rs[0].download_url
    assert rs[0].indexer_name == "YTS"


def test_knaben():
    data = {
        "hits": [
            {"title": "Thing 1080p", "magnetUrl": "magnet:?xt=urn:btih:aaa", "seeders": 100, "peers": 10, "bytes": 123456, "tracker": "TPB"},
            {"title": "no link at all"},
        ]
    }
    f = FakeFetcher(data=data)
    rs = run("knaben", f)
    assert len(rs) == 1
    r = rs[0]
    assert r.indexer_name == "Knaben (TPB)"
    assert r.seeders == 100
    assert r.peers == 10
    assert r.size == 123456
    assert r.download_url == "magnet:?xt=urn:btih:aaa"
    assert len(f.calls) == 1
    url, body = f.calls[0]
    assert url.endswith("/v1")
    assert body["query"] == "test"


def test_nyaa():
    xml = '''\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:nyaa="https://nyaa.si/xmlns/nyaa">
  <channel>
    <item>
      <title>[Group] Show - 01 [1080p]</title>
      <link>https://nyaa.si/download/1.torrent</link>
      <nyaa:seeders>40</nyaa:seeders>
      <nyaa:leechers>2</nyaa:leechers>
      <nyaa:size>1.2 GiB</nyaa:size>
      <nyaa:infoHash>ABCDEF0123456789ABCDEF0123456789ABCDEF01</nyaa:infoHash>
    </item>
  </channel>
</rss>'''

    rs = run("nyaa", FakeFetcher(text=xml))
    assert len(rs) == 1
    r = rs[0]
    assert r.title == "[Group] Show - 01 [1080p]"
    assert r.download_url.startswith("magnet:?xt=urn:btih:abcdef0123456789")
    assert r.seeders == 40
    assert r.peers == 2
    assert r.size == parse_size("1.2 GiB")
    assert r.indexer_name == "Nyaa"


def test_limetorrents():
    xml = '''\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Some Movie 2024 1080p</title>
      <enclosure url="https://itorrents.org/torrent/ABC.torrent" length="123" type="application/x-bittorrent"/>
      <description>Seeds: 12 , Leechers: 3 , Size: 1.3 GB</description>
    </item>
  </channel>
</rss><script>cf junk</script>'''

    rs = run("limetorrents", FakeFetcher(text=xml))
    assert len(rs) == 1
    r = rs[0]
    assert r.title == "Some Movie 2024 1080p"
    assert r.download_url == "https://itorrents.org/torrent/ABC.torrent"
    assert r.seeders == 12
    assert r.peers == 3
    assert r.size == parse_size("1.3 GB")


def test_torrentdownloads():
    xml = '''\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Linux ISO</title>
      <size>734003200</size>
      <seeders>4</seeders>
      <leechers>1</leechers>
      <info_hash>0123456789ABCDEF0123456789ABCDEF01234567</info_hash>
    </item>
    <item>
      <title>no hash</title>
    </item>
  </channel>
</rss>'''

    rs = run("torrentdownloads", FakeFetcher(text=xml))
    assert len(rs) == 1
    r = rs[0]
    assert r.title == "Linux ISO"
    assert r.download_url.startswith("magnet:?xt=urn:btih:0123456789abcdef")
    assert r.size == 734003200
    assert r.seeders == 4
    assert r.peers == 1


def test_eztv():
    html = """<table><tr><td><a href="/ep/123/show-s01e01/" class="epinfo" title="Show S01E01 1080p (1.2 GB)">Show S01E01 1080p</a></td><td><a href="magnet:?xt=urn:btih:abc&amp;dn=x" class="magnet">m</a></td><td align="center" class="forum_thread_post">1.2 GB</td><td align="center" class="forum_thread_post">1 day</td><td align="center" class="forum_thread_post_end"><font color="green">55</font></td></tr></table>"""
    rs = run("eztv", FakeFetcher(text=html))
    assert len(rs) == 1
    r = rs[0]
    assert r.title == "Show S01E01 1080p"
    assert r.download_url == "magnet:?xt=urn:btih:abc&dn=x"
    assert r.seeders == 55
    assert r.size == parse_size("1.2 GB")
    assert r.indexer_name == "EZTV"


def test_1337x():
    html = """<td class="coll-1 name"><a href="/sub/1/"><i></i></a><a href="/torrent/1/Some-Release/">Some Release 1080p</a></td><td class="coll-2 seeds">120</td><td class="coll-3 leeches">8</td><td class="coll-date">x</td><td class="coll-4 size mob-uploader">2.1 GB<span class="seeds">120</span></td>
<a href="magnet:?xt=urn:btih:def&amp;dn=y">Magnet</a>"""
    rs = run("1337x", FakeFetcher(text=html))
    assert len(rs) == 1
    r = rs[0]
    assert r.title == "Some Release 1080p"
    assert r.download_url.startswith("magnet:?xt=urn:btih:def&dn=y")
    assert r.seeders == 120
    assert r.peers == 8
    assert r.size == parse_size("2.1 GB")
    assert r.indexer_name == "1337x"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"{len(tests)} checks passed")
