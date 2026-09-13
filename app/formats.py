"""Custom formats (M17): named rule sets matched against parse_release() output, each scored per quality profile. A release's format score is the sum of the scores of every format it matches."""

import json
import re
from typing import List, Dict, Tuple, Any

from sqlalchemy.orm import Session

from app.models import CustomFormat, ProfileFormatScore, QualityProfile
from app.parser import parse_release


FIELDS = ("title", "quality", "source", "codec", "hdr", "audio", "group", "language")
OPS = ("contains", "equals", "regex")


BUILTIN: List[Dict[str, Any]] = [
    {
        "name": "Remux",
        "rules": [{"field": "source", "op": "equals", "value": "remux", "negate": False}],
        "score": 60
    },
    {
        "name": "BluRay",
        "rules": [{"field": "source", "op": "equals", "value": "bluray", "negate": False}],
        "score": 40
    },
    {
        "name": "WEB-DL",
        "rules": [{"field": "source", "op": "equals", "value": "web-dl", "negate": False}],
        "score": 30
    },
    {
        "name": "WEBRip",
        "rules": [{"field": "source", "op": "equals", "value": "webrip", "negate": False}],
        "score": 10
    },
    {
        "name": "HDTV",
        "rules": [{"field": "source", "op": "equals", "value": "hdtv", "negate": False}],
        "score": -10
    },
    {
        "name": "CAM / TS / Screener",
        "rules": [{"field": "source", "op": "equals", "value": "cam", "negate": False}],
        "score": -1000
    },
    {
        "name": "x265 / HEVC",
        "rules": [{"field": "codec", "op": "equals", "value": "x265", "negate": False}],
        "score": 20
    },
    {
        "name": "AV1",
        "rules": [{"field": "codec", "op": "equals", "value": "av1", "negate": False}],
        "score": 0
    },
    {
        "name": "HDR",
        "rules": [{"field": "hdr", "op": "regex", "value": "^hdr", "negate": False}],
        "score": 25
    },
    {
        "name": "HDR10+",
        "rules": [{"field": "hdr", "op": "equals", "value": "hdr10+", "negate": False}],
        "score": 30
    },
    {
        "name": "Dolby Vision",
        "rules": [{"field": "hdr", "op": "equals", "value": "dv", "negate": False}],
        "score": 35
    },
    {
        "name": "Atmos",
        "rules": [{"field": "audio", "op": "equals", "value": "atmos", "negate": False}],
        "score": 15
    },
    {
        "name": "TrueHD / DTS-HD",
        "rules": [{"field": "audio", "op": "regex", "value": "^(truehd|dts-hd)$", "negate": False}],
        "score": 10
    },
    {
        "name": "Multi-language",
        "rules": [{"field": "language", "op": "contains", "value": "multi", "negate": False}],
        "score": 0
    },
    {
        "name": "Dual audio",
        "rules": [{"field": "language", "op": "contains", "value": "dual", "negate": False}],
        "score": 0
    },
    {
        "name": "Foreign language only",
        "rules": [{"field": "language", "op": "regex", "value": "^(fr|de|es|it|ja|ko|hi|ru|pt|zh)$", "negate": False}],
        "score": -200
    }
]


def rules_of(fmt: CustomFormat) -> List[Dict[str, Any]]:
    """Parse the JSON rules string of a custom format."""
    try:
        rules = json.loads(fmt.rules or "[]")
        if not isinstance(rules, list):
            return []
        return rules
    except (json.JSONDecodeError, TypeError):
        return []


def rule_matches(rule: Dict[str, Any], attrs: Dict[str, Any]) -> bool:
    """Check if a single rule matches the parsed release attributes."""
    field = rule.get("field")
    op = rule.get("op")
    value = rule.get("value", "")
    negate = bool(rule.get("negate"))

    # Special handling for language field
    if field == "language":
        subject = " ".join(attrs.get("languages") or [])
    else:
        subject = str(attrs.get(field, "") or "")

    match_result = False

    if op == "contains":
        match_result = value.lower() in subject.lower()
    elif op == "equals":
        match_result = subject.lower() == value.lower()
    elif op == "regex":
        try:
            match_result = bool(re.search(value, subject, re.IGNORECASE))
        except re.error:
            match_result = False
    else:
        # Unknown operation
        match_result = False

    if negate:
        return not match_result
    return match_result


def format_matches(rules: List[Dict[str, Any]], attrs: Dict[str, Any]) -> bool:
    """Check if all rules in a list match the parsed release attributes."""
    if not rules:
        return False
    return all(rule_matches(rule, attrs) for rule in rules)


def validate_rules(rules) -> List[Dict[str, Any]]:
    """
    Validate that rules is a list of dicts with valid fields and operations.
    
    Raises ValueError on invalid input.
    Returns cleaned list of rules.
    """
    if not isinstance(rules, list):
        raise ValueError("Rules must be a list")

    cleaned_rules = []
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("Each rule must be a dictionary")
        
        field = rule.get("field")
        op = rule.get("op")
        value = rule.get("value", "")
        negate = bool(rule.get("negate"))

        if field not in FIELDS:
            raise ValueError(f"Invalid field: {field}")
        if op not in OPS:
            raise ValueError(f"Invalid operation: {op}")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Value must be a non-empty string")
        
        # Validate regex compilation
        if op == "regex":
            try:
                re.compile(value)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {value} - {e}")

        cleaned_rules.append({
            "field": field,
            "op": op,
            "value": value.strip(),
            "negate": negate
        })

    return cleaned_rules


def seed_builtin(db: Session) -> None:
    """Seed the database with built-in custom formats and their scores for all profiles."""
    # Get or create builtin formats
    existing_formats = {fmt.name: fmt.id for fmt in db.query(CustomFormat).filter_by(builtin=True)}
    
    format_ids = []
    for builtin_fmt in BUILTIN:
        name = builtin_fmt["name"]
        rules = builtin_fmt["rules"]
        score = builtin_fmt["score"]

        if name not in existing_formats:
            # Create the format
            fmt = CustomFormat(
                name=name,
                rules=json.dumps(rules),
                builtin=True
            )
            db.add(fmt)
            db.flush()  # Get the ID without committing
            format_id = fmt.id
        else:
            format_id = existing_formats[name]

        format_ids.append(format_id)

    # Commit all formats first
    db.commit()

    # Now create profile score entries for each builtin format and every quality profile
    profiles = db.query(QualityProfile).all()
    
    for profile in profiles:
        for fmt_id in format_ids:
            # Check if this combination already exists
            existing_score = db.query(ProfileFormatScore)\
                .filter_by(profile_id=profile.id, format_id=fmt_id)\
                .first()
            
            if not existing_score:
                score_entry = ProfileFormatScore(
                    profile_id=profile.id,
                    format_id=fmt_id,
                    score=BUILTIN[format_ids.index(fmt_id)]["score"]
                )
                db.add(score_entry)

    db.commit()


def profile_scores(db: Session, profile: QualityProfile) -> List[Tuple[CustomFormat, int]]:
    """Get all custom formats with their scores for a given quality profile."""
    # Get the score entries for this profile
    score_entries = db.query(ProfileFormatScore)\
        .filter_by(profile_id=profile.id)\
        .all()
    
    # Create a mapping of format_id -> score
    score_map = {entry.format_id: entry.score for entry in score_entries}
    
    # Get all formats ordered by id
    formats = db.query(CustomFormat).order_by(CustomFormat.id).all()
    
    # Pair each format with its score (0 if not found)
    return [(fmt, score_map.get(fmt.id, 0)) for fmt in formats]


def score_title(title: str, scored: List[Tuple[CustomFormat, int]]) -> Tuple[int, List[str]]:
    """Score a title against a list of (format, score) tuples."""
    attrs = parse_release(title)
    
    total_score = 0
    matched_formats = []
    
    for fmt, score in scored:
        rules = rules_of(fmt)
        if format_matches(rules, attrs):
            total_score += score
            matched_formats.append(fmt.name)
            
    return total_score, matched_formats
