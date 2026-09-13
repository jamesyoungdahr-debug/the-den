"""Custom formats and quality profiles (M17): CRUD for formats, profile editing with per-format scores, and a title test endpoint."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth, formats
from app.deps import get_db
from app.models import CustomFormat, ProfileFormatScore, QualityProfile
from app.parser import parse_release

router = APIRouter(prefix="/api/formats", tags=["formats"], dependencies=[Depends(auth.require_admin)])


class FormatIn(BaseModel):
    name: str
    rules: list[dict] = []


class ProfileIn(BaseModel):
    name: str | None = None
    allowed_qualities: str | None = None
    cutoff: str | None = None
    min_format_score: int | None = None
    upgrade_until_score: int | None = None
    scores: dict[int, int] | None = None


class TestIn(BaseModel):
    title: str
    profile_id: int | None = None


def _format_out(fmt: CustomFormat) -> dict:
    return {"id": fmt.id, "name": fmt.name, "rules": formats.rules_of(fmt), "builtin": fmt.builtin}


def _profile_out(db, profile) -> dict:
    return {
        "id": profile.id,
        "name": profile.name,
        "allowed_qualities": profile.allowed_qualities,
        "cutoff": profile.cutoff,
        "min_format_score": profile.min_format_score,
        "upgrade_until_score": profile.upgrade_until_score,
        "scores": {row.format_id: row.score for row in db.query(ProfileFormatScore).filter(ProfileFormatScore.profile_id == profile.id)}
    }


def _clean_rules(rules) -> list[dict]:
    try:
        return formats.validate_rules(rules)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.get("/profiles")
def list_profiles(db: Session = Depends(get_db)):
    profiles = db.query(QualityProfile).order_by(QualityProfile.id).all()
    return [_profile_out(db, p) for p in profiles]


@router.patch("/profiles/{profile_id}")
def update_profile(profile_id: int, payload: ProfileIn, db: Session = Depends(get_db)):
    profile = db.get(QualityProfile, profile_id)
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "name is required")
        profile.name = name

    if payload.allowed_qualities is not None:
        parts = [q.strip() for q in payload.allowed_qualities.split(",") if q.strip()]
        if not parts:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "allowed_qualities is required")
        profile.allowed_qualities = ",".join(parts)

    if payload.cutoff is not None:
        profile.cutoff = payload.cutoff

    if profile.cutoff not in profile.allowed_qualities.split(","):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cutoff must be one of the allowed qualities")

    if payload.min_format_score is not None:
        profile.min_format_score = payload.min_format_score

    if payload.upgrade_until_score is not None:
        profile.upgrade_until_score = payload.upgrade_until_score

    if payload.scores is not None:
        for format_id, score in payload.scores.items():
            fmt = db.get(CustomFormat, format_id)
            if not fmt:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown format id {format_id}")

            row = db.query(ProfileFormatScore).filter(
                ProfileFormatScore.profile_id == profile.id,
                ProfileFormatScore.format_id == format_id
            ).first()

            if row:
                row.score = score
            else:
                db.add(ProfileFormatScore(profile_id=profile.id, format_id=format_id, score=score))

    db.commit()
    return _profile_out(db, profile)


@router.post("/test")
def test_title(payload: TestIn, db: Session = Depends(get_db)):
    profile = db.get(QualityProfile, payload.profile_id) if payload.profile_id else db.query(QualityProfile).first()
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")

    score, names = formats.score_title(payload.title, formats.profile_scores(db, profile))
    return {"attrs": parse_release(payload.title), "score": score, "formats": names}


@router.get("")
def list_formats(db: Session = Depends(get_db)):
    fmts = db.query(CustomFormat).order_by(CustomFormat.id).all()
    return [_format_out(f) for f in fmts]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_format(payload: FormatIn, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "name is required")

    rules = _clean_rules(payload.rules)

    existing = db.query(CustomFormat).filter(CustomFormat.name == name).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A format with that name already exists")

    fmt = CustomFormat(name=name, rules=json.dumps(rules), builtin=False)
    db.add(fmt)
    db.commit()
    db.refresh(fmt)
    return _format_out(fmt)


@router.put("/{format_id}")
def update_format(format_id: int, payload: FormatIn, db: Session = Depends(get_db)):
    fmt = db.get(CustomFormat, format_id)
    if not fmt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Format not found")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "name is required")

    if fmt.builtin and name != fmt.name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Built-in formats keep their name")

    existing = db.query(CustomFormat).filter(
        CustomFormat.name == name,
        CustomFormat.id != format_id
    ).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A format with that name already exists")

    fmt.name = name
    fmt.rules = json.dumps(_clean_rules(payload.rules))
    db.commit()
    return _format_out(fmt)


@router.delete("/{format_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_format(format_id: int, db: Session = Depends(get_db)):
    fmt = db.get(CustomFormat, format_id)
    if not fmt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Format not found")

    if fmt.builtin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Built-in formats cannot be deleted")

    db.query(ProfileFormatScore).filter(ProfileFormatScore.format_id == format_id).delete()
    db.delete(fmt)
    db.commit()
