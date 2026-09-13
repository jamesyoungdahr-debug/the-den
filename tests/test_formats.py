"""M17 checks: parse_release on real release titles and custom-format scoring. Run from the repo root."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.parser import parse_release
from app import formats
from app.models import CustomFormat
import json

fails = []

def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ("" if ok else f"  got={got!r} want={want!r}"))
    if not ok:
        fails.append(name)

# Section 1: parser tests

CASES = [
    ("Dune.Part.Two.2024.2160p.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265-FLUX", {"quality": "2160p", "source": "web-dl", "codec": "x265", "hdr": "dv", "audio": "atmos", "group": "FLUX"}),
    ("The.Bear.S03E01.1080p.WEB.H264-NHTFS[TGx]", {"source": "web", "codec": "x264", "group": "NHTFS"}),
    ("Oppenheimer.2023.1080p.BluRay.x264.DTS-HD.MA.5.1-FGT", {"source": "bluray", "audio": "dts-hd", "group": "FGT"}),
    ("Shogun.2024.S01E05.2160p.AMZN.WEB-DL.DDP5.1.HDR10+.HEVC-KOGi", {"hdr": "hdr10+", "audio": "ddp", "codec": "x265"}),
    ("Inception 2010 REMUX 2160p UHD BluRay TrueHD Atmos 7.1 HDR-EPSiLON", {"source": "remux", "hdr": "hdr", "audio": "atmos", "group": "EPSiLON"}),
    ("Parasite.2019.MULTi.1080p.BluRay.x265-Ozlem", {"languages": ["multi"], "codec": "x265"}),
    ("Spirited.Away.2001.JAPANESE.1080p.BluRay.H264.AAC-VXT", {"languages": ["ja"], "audio": "aac"}),
    ("The.Matrix.1999.1080p.HDTV.x264", {"source": "hdtv", "group": ""}),
    ("Movie.Title.2024.HDCAM.x264-QRips", {"source": "cam", "quality": "unknown"}),
    ("Show.S02E03.German.DL.1080p.WEBRip.x264-TvR", {"source": "webrip", "languages": ["de"]}),
    ("Some.Film.2022.1080p.WEB-DL.DUAL.AUDIO.AC3-RARBG.mkv", {"languages": ["dual"], "audio": "dd", "group": "RARBG"}),
    ("Unforgiven.1992.1080p.BluRay.x264-AMIABLE", {"source": "bluray"}),  # not web-dl: 'nf' inside a word must not match
    ("Ghosts.US.S01E01.720p.HDTV.x264-SYNCOPY", {"source": "hdtv"}),  # not cam: 'ts' inside a word
    ("Scream.1996.DVDRip.XviD-FiCO", {"source": "dvd", "codec": "xvid"}),
    ("Blade.Runner.2049.2017.2160p.UHD.BluRay.x265.10bit.HDR.TrueHD.7.1.Atmos-SWTYBLZ", {"hdr": "hdr", "audio": "atmos", "codec": "x265"}),
    ("Arcane.S01E01.1080p.NF.WEB-DL.DDP5.1.x264-NTb", {"source": "web-dl", "audio": "ddp", "group": "NTb"}),
    ("Old.Movie.1955.480p.DVD.x264-Grp", {"quality": "480p", "source": "dvd"}),
    ("Film.2023.1080p.AV1.Opus-Grp", {"codec": "av1"}),
    ("Series.S01E02.FRENCH.1080p.WEB.H264-FW", {"languages": ["fr"]}),
    ("Title.2020.1080p.BluRay.FLAC.2.0.x264-DON", {"audio": "flac", "group": "DON"}),
]

for title, expected in CASES:
    result = parse_release(title)
    for key, want_value in expected.items():
        check(f"parse_release('{title}')[{key!r}]", result[key], want_value)

# Section 2: scoring tests

scored = [
    (CustomFormat(id=1, name="BluRay", rules='[{"field":"source","op":"equals","value":"bluray","negate":false}]', builtin=True), 40),
    (CustomFormat(id=2, name="No RARBG", rules='[{"field":"group","op":"equals","value":"RARBG","negate":true}]', builtin=False), 5),
    (CustomFormat(id=3, name="CAM", rules='[{"field":"source","op":"equals","value":"cam","negate":false}]', builtin=True), -1000)
]

check("score_title('Movie.2020.1080p.BluRay.x264-Grp', scored)", formats.score_title("Movie.2020.1080p.BluRay.x264-Grp", scored), (45, ["BluRay", "No RARBG"]))
check("score_title('Movie.2020.1080p.BluRay.x264-RARBG', scored)", formats.score_title("Movie.2020.1080p.BluRay.x264-RARBG", scored), (40, ["BluRay"]))
check("score_title('Movie.2020.HDCAM-RARBG', scored)", formats.score_title("Movie.2020.HDCAM-RARBG", scored), (-1000, ["CAM"]))

# Additional format matching tests

check("formats.format_matches([], {'title': 'x'}) is False", formats.format_matches([], {"title": "x"}), False)
check("formats.rule_matches({'field': 'language', 'op': 'contains', 'value': 'multi'}, {'languages': ['multi', 'en']}) is True", formats.rule_matches({"field": "language", "op": "contains", "value": "multi"}, {"languages": ["multi", "en"]}), True)
check("formats.rule_matches({'field': 'title', 'op': 'regex', 'value': '(', 'negate': False}, {'title': 'x'}) is False", formats.rule_matches({"field": "title", "op": "regex", "value": "(", "negate": False}, {"title": "x"}), False)

# Validate rules tests

try:
    formats.validate_rules([{"field": "nope", "op": "contains", "value": "x"}])
    check("validate_rules with invalid field raises ValueError", True, False)
except ValueError:
    check("validate_rules with invalid field raises ValueError", True, True)

try:
    formats.validate_rules([{"field": "title", "op": "regex", "value": "("}])
    check("validate_rules with bad regex raises ValueError", True, False)
except ValueError:
    check("validate_rules with bad regex raises ValueError", True, True)

cleaned = formats.validate_rules([{"field": "group", "op": "equals", "value": " FLUX ", "negate": 1}])
check("validate_rules strips whitespace and converts negate to bool", cleaned, [{"field": "group", "op": "equals", "value": "FLUX", "negate": True}])

print(f"\n{len(fails)} FAILURE(S)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)