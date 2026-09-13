"""Rename existing library files to the current Plex-naming convention (E4):
preview every file that's out of date, apply one, or apply everything at once."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, renamer
from app.deps import get_db

router = APIRouter(prefix="/api/rename", tags=["rename"], dependencies=[Depends(auth.require_admin)])


@router.get("/preview")
def preview(db: Session = Depends(get_db)):
    return renamer.all_plans(db)


@router.post("/apply")
def apply_one(kind: str, id: int, db: Session = Depends(get_db)):
    try:
        return renamer.apply_plan(db, kind, id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except OSError as exc:
        raise HTTPException(500, str(exc))


@router.post("/apply-all")
def apply_all(db: Session = Depends(get_db)):
    results = []
    for plan in renamer.all_plans(db):
        try:
            renamer.apply_plan(db, plan["kind"], plan["id"])
            results.append({**plan, "ok": True})
        except Exception as exc:
            results.append({**plan, "ok": False, "error": str(exc)})
    return results
