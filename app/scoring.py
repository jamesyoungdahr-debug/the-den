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


def _rank(quality: str, allowed: list[str]) -> int:
    """Position in the profile's best-first list; len(allowed) when not allowed/unknown."""
    return allowed.index(quality) if quality in allowed else len(allowed)


def is_upgradable(file_quality: str | None, file_score: int, profile: QualityProfile) -> bool:
    """A title with a file still wants a better one while its quality is below the profile
    cutoff, or its format score is below profile.upgrade_until_score (0 disables that)."""
    allowed = [q.strip() for q in profile.allowed_qualities.split(",")]
    if _rank(file_quality or "", allowed) > _rank(profile.cutoff, allowed):
        return True
    return bool(profile.upgrade_until_score) and (file_score or 0) < profile.upgrade_until_score


def beats_current(quality: str, score: int, file_quality: str | None, file_score: int, profile: QualityProfile, margin: int = 10) -> bool:
    """True when a candidate is worth replacing the file on disk: a strictly better allowed
    quality, or the same quality with a format score at least `margin` higher."""
    allowed = [q.strip() for q in profile.allowed_qualities.split(",")]
    new_rank, old_rank = _rank(quality, allowed), _rank(file_quality or "", allowed)
    if new_rank >= len(allowed):
        return False
    if new_rank < old_rank:
        return True
    return new_rank == old_rank and score >= (file_score or 0) + margin
