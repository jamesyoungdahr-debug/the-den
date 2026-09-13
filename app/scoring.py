from app.models import QualityProfile
from app.parser import parse_quality
from app.torznab import Release


def best_release(releases: list[Release], profile: QualityProfile, scores: dict[str, int] | None = None) -> Release | None:
    """Pick the best release: best allowed quality first, then highest custom-format score
    (from `scores`, keyed by release title, default 0), then most seeders. Releases whose
    format score is below profile.min_format_score are never picked."""
    allowed = [q.strip() for q in profile.allowed_qualities.split(",")]
    floor = profile.min_format_score or 0

    def rank(r: Release):
        quality = parse_quality(r.title)
        if quality not in allowed:
            return None
        score = (scores or {}).get(r.title, 0)
        if score < floor:
            return None
        return (allowed.index(quality), -score, -(r.seeders or 0))

    candidates = [(rank(r), r) for r in releases]
    candidates = [(rk, r) for rk, r in candidates if rk is not None]
    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0])
    return candidates[0][1]
