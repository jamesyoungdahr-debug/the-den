import re

# Order matters: check most specific first (2160p before it could confuse with 1080p, etc).
_QUALITY_PATTERNS = [
    ("2160p", re.compile(r"2160p|\b4k\b", re.IGNORECASE)),
    ("1080p", re.compile(r"1080p", re.IGNORECASE)),
    ("720p", re.compile(r"720p", re.IGNORECASE)),
    ("480p", re.compile(r"480p|sdtv", re.IGNORECASE)),
]


def parse_quality(release_title: str) -> str:
    for quality, pattern in _QUALITY_PATTERNS:
        if pattern.search(release_title):
            return quality
    return "unknown"
