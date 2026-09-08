from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db
from app.download_check import check_and_import
from app.models import DownloadRecord
from app.schemas import DownloadRecordOut

router = APIRouter(prefix="/downloads", tags=["downloads"])


@router.get("", response_model=list[DownloadRecordOut])
def list_downloads(db: Session = Depends(get_db)):
    return db.query(DownloadRecord).all()


@router.post("/{download_id}/check", response_model=DownloadRecordOut)
async def check_download(download_id: int, db: Session = Depends(get_db)):
    record = db.get(DownloadRecord, download_id)
    if not record:
        raise HTTPException(404, "Download not found")
    try:
        await check_and_import(db, record)
    except Exception as exc:
        raise HTTPException(502, f"Failed to reach download client: {exc}")
    db.refresh(record)
    return record
