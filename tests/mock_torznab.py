"""Tiny stand-in for a real Torznab indexer, for testing our client against
real HTTP + real XML without needing a live tracker account."""

from fastapi import FastAPI, Response

app = FastAPI()

CAPS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<caps><server title="Mock Indexer" version="1.0"/></caps>"""

SEARCH_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
<channel>
  <item>
    <title>{query}.2024.1080p.BluRay.x264-GROUP</title>
    <link>http://mock/download/1</link>
    <enclosure url="http://mock/download/1" length="4294967296" type="application/x-bittorrent"/>
    <torznab:attr name="size" value="4294967296"/>
    <torznab:attr name="seeders" value="42"/>
    <torznab:attr name="peers" value="10"/>
  </item>
  <item>
    <title>{query}.2024.720p.WEB-DL.x264-GROUP</title>
    <link>http://mock/download/2</link>
    <enclosure url="http://mock/download/2" length="1500000000" type="application/x-bittorrent"/>
    <torznab:attr name="size" value="1500000000"/>
    <torznab:attr name="seeders" value="7"/>
    <torznab:attr name="peers" value="2"/>
  </item>
</channel>
</rss>"""


@app.get("/api")
def api(t: str, q: str = "", apikey: str = ""):
    if t == "caps":
        return Response(CAPS_XML, media_type="application/xml")
    if t == "search":
        return Response(SEARCH_XML_TEMPLATE.format(query=q or "Sample"), media_type="application/xml")
    return Response(status_code=400)
