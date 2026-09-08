from app.models import QualityProfile
from app.parser import parse_quality
from app.torznab import Release


def best_release(releases: list[Release], profile: QualityProfile) -> Release | None:
    """Pick the best release: best allowed quality first, then most seeders."""
    allowed = [q.strip() for q in profile.allowed_qualities.split(",")]

    def rank(r: Release):
        quality = parse_quality(r.title)
        if quality not in allowed:
            return None
        return (allowed.index(quality), -(r.seeders or 0))

    candidates = [(rank(r), r) for r in releases]
    candidates = [(rk, r) for rk, r in candidates if rk is not None]
    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0])
    return candidates[0][1]
