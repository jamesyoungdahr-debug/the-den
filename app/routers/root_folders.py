"""Root folders (E2): CRUD for named library folders per media type, mirroring
app/routers/import_lists.py's shape but simpler (no sync action)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth
from app.deps import get_db
from app.models import RootFolder

router = APIRouter(prefix="/api/root-folders", tags=["root-folders"], dependencies=[Depends(auth.require_admin)])

MEDIA_TYPES = ("movie", "tv")


class RootFolderIn(BaseModel):
    name: str
    media_type: str
    path: str
    is_default: bool = False


def _out(rf: RootFolder) -> dict:
    return {"id": rf.id, "name": rf.name, "media_type": rf.media_type, "path": rf.path, "is_default": rf.is_default}


def _validate(media_type: str, path: str) -> None:
    if media_type not in MEDIA_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"media_type must be one of {MEDIA_TYPES}")
    if not path.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "path is required")


def _clear_other_defaults(db: Session, media_type: str, except_id: int | None = None) -> None:
    """Only one default per media type; making one the default un-defaults the rest."""
    q = db.query(RootFolder).filter(RootFolder.media_type == media_type, RootFolder.is_default == True)  # noqa: E712
    if except_id is not None:
        q = q.filter(RootFolder.id != except_id)
    q.update({"is_default": False}, synchronize_session=False)


@router.get("")
def list_root_folders(db: Session = Depends(get_db)):
    return [_out(rf) for rf in db.query(RootFolder).order_by(RootFolder.id).all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_root_folder(body: RootFolderIn, db: Session = Depends(get_db)):
    _validate(body.media_type, body.path)
    rf = RootFolder(name=body.name, media_type=body.media_type, path=body.path.strip(), is_default=body.is_default)
    db.add(rf)
    db.flush()
    if body.is_default:
        _clear_other_defaults(db, body.media_type, except_id=rf.id)
    db.commit()
    db.refresh(rf)
    return _out(rf)


@router.put("/{root_folder_id}")
def update_root_folder(root_folder_id: int, body: RootFolderIn, db: Session = Depends(get_db)):
    rf = db.get(RootFolder, root_folder_id)
    if rf is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    _validate(body.media_type, body.path)
    rf.name = body.name
    rf.media_type = body.media_type
    rf.path = body.path.strip()
    rf.is_default = body.is_default
    if body.is_default:
        _clear_other_defaults(db, body.media_type, except_id=rf.id)
    db.commit()
    return _out(rf)


@router.delete("/{root_folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_root_folder(root_folder_id: int, db: Session = Depends(get_db)):
    rf = db.get(RootFolder, root_folder_id)
    if rf is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(rf)
    db.commit()
