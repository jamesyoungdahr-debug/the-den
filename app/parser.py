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


def _first(patterns, title) -> str:
    for value, pattern in patterns:
        if pattern.search(title):
            return value
    return ""


_SOURCE_PATTERNS = [
    ("remux", re.compile(r"remux", re.IGNORECASE)),
    ("bluray", re.compile(r"bluray|blu-ray|bdrip|brrip", re.IGNORECASE)),
    ("web-dl", re.compile(r"web[\s.\-_]?dl|\b(?:amzn|nf|dsnp|atvp|hmax|pcok)\b", re.IGNORECASE)),
    ("webrip", re.compile(r"webrip|web-rip|web\.rip", re.IGNORECASE)),
    ("web", re.compile(r"\bweb\b", re.IGNORECASE)),
    ("hdtv", re.compile(r"hdtv|pdtv", re.IGNORECASE)),
    ("dvd", re.compile(r"\bdvd(?:rip)?\b", re.IGNORECASE)),
    ("cam", re.compile(r"\b(?:cam|hdcam|ts|tc|telesync|telecine|hdts|scr|screener)\b", re.IGNORECASE)),
]

_CODEC_PATTERNS = [
    ("x265", re.compile(r"x265|h\.?265|hevc", re.IGNORECASE)),
    ("x264", re.compile(r"x264|h\.?264|avc", re.IGNORECASE)),
    ("av1", re.compile(r"\bav1\b", re.IGNORECASE)),
    ("xvid", re.compile(r"xvid|divx", re.IGNORECASE)),
]

_HDR_PATTERNS = [
    ("dv", re.compile(r"\bdv\b|dolby[\s.\-_]?vision|dovi", re.IGNORECASE)),
    ("hdr10+", re.compile(r"hdr10\+|hdr10plus", re.IGNORECASE)),
    ("hdr", re.compile(r"\bhdr\b|hdr10|\bpq\b|hlg", re.IGNORECASE)),
]

_AUDIO_PATTERNS = [
    ("atmos", re.compile(r"atmos", re.IGNORECASE)),
    ("truehd", re.compile(r"truehd|true-hd", re.IGNORECASE)),
    ("dts-hd", re.compile(r"dts[\s.\-_]?hd|dts[\s.\-_]?x|dtsx", re.IGNORECASE)),
    ("dts", re.compile(r"\bdts\b", re.IGNORECASE)),
    ("ddp", re.compile(r"ddp|dd\+|eac3|e-ac-3", re.IGNORECASE)),
    ("dd", re.compile(r"\bdd\b|ac3|dd5\.1|dd2\.0", re.IGNORECASE)),
    ("aac", re.compile(r"\baac\b", re.IGNORECASE)),
    ("flac", re.compile(r"\bflac\b", re.IGNORECASE)),
]

_LANGUAGE_PATTERNS = [
    ("multi", re.compile(r"\bmulti\b", re.IGNORECASE)),
    ("dual", re.compile(r"dual[\s.\-_]?audio", re.IGNORECASE)),
    ("en", re.compile(r"\benglish\b|\beng\b", re.IGNORECASE)),
    ("fr", re.compile(r"\bfrench\b|\bvff\b|\bvfq\b|\btruefrench\b", re.IGNORECASE)),
    ("de", re.compile(r"\bgerman\b|\bger\b", re.IGNORECASE)),
    ("es", re.compile(r"\bspanish\b|\bspa\b|\bcastellano\b|\blatino\b", re.IGNORECASE)),
    ("it", re.compile(r"\bitalian\b|\bita\b", re.IGNORECASE)),
    ("ja", re.compile(r"\bjapanese\b|\bjpn\b", re.IGNORECASE)),
    ("ko", re.compile(r"\bkorean\b|\bkor\b", re.IGNORECASE)),
    ("hi", re.compile(r"\bhindi\b", re.IGNORECASE)),
    ("ru", re.compile(r"\brussian\b|\brus\b", re.IGNORECASE)),
    ("pt", re.compile(r"\bportuguese\b|\bpt-br\b|\bbrazilian\b", re.IGNORECASE)),
    ("zh", re.compile(r"\bchinese\b|\bmandarin\b|\bcantonese\b", re.IGNORECASE)),
]

_NON_GROUP_WORDS = {
    "web", "dl", "rip", "hdtv", "bluray", "x264", "x265", "hevc", "aac", "ddp",
    "dts", "remux", "1080p", "720p", "2160p", "480p", "web-dl"
}

def parse_release(release_title: str) -> dict:
    """Everything the custom-format rules can look at, parsed from a release title:
    {"quality": str, "source": str, "codec": str, "hdr": str, "audio": str, "group": str, "languages": list[str], "title": str}
    Unknown values are "" (or [] for languages). title is the original string."""
    
    quality = parse_quality(release_title)
    source = _first(_SOURCE_PATTERNS, release_title)
    codec = _first(_CODEC_PATTERNS, release_title)
    hdr = _first(_HDR_PATTERNS, release_title)
    audio = _first(_AUDIO_PATTERNS, release_title)
    
    # Parse languages
    languages = []
    for code, pattern in _LANGUAGE_PATTERNS:
        if pattern.search(release_title) and code not in languages:
            languages.append(code)
    
    # Parse group
    group = ""
    match = re.search(r"-([A-Za-z0-9]+)(?:\[[^\]]*\])?(?:\.(?:mkv|mp4|avi))?\s*$", release_title)
    if match:
        potential_group = match.group(1)
        if potential_group.lower() not in _NON_GROUP_WORDS:
            group = potential_group
    
    return {
        "quality": quality,
        "source": source,
        "codec": codec,
        "hdr": hdr,
        "audio": audio,
        "group": group,
        "languages": languages,
        "title": release_title
    }
