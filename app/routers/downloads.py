from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import qbittorrent
from app.deps import get_db
from app.importer import import_finished_download
from app.models import DownloadRecord, Movie
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
    if record.status == "imported":
        return record

    try:
        info = await qbittorrent.get_by_category(record.category)
    except Exception as exc:
        raise HTTPException(502, f"Failed to reach download client: {exc}")

    if info is None:
        record.status = "queued"
    elif info.get("progress", 0) >= 1.0:
        movie = db.get(Movie, record.movie_id)
        if import_finished_download(info, movie):
            movie.has_file = True
            record.status = "imported"
        else:
            record.status = "completed"  # finished downloading, import didn't find a video file
    else:
        record.status = "downloading"

    db.commit()
    db.refresh(record)
    return record
