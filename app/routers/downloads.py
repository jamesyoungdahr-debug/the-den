from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, automation, blocklist
from app.deps import get_db
from app.download_check import check_and_import, fail_download
from app.models import BlocklistEntry, DownloadRecord
from app.schemas import DownloadRecordOut

router = APIRouter(prefix="/downloads", tags=["downloads"], dependencies=[Depends(auth.require_admin)])


@router.get("", response_model=list[DownloadRecordOut])
def list_downloads(db: Session = Depends(get_db)):
    return db.query(DownloadRecord).all()


@router.get("/blocklist", response_model=list[dict])
def list_blocklist(db: Session = Depends(get_db)):
    return [_entry_out(e) for e in blocklist.active(db)]


@router.delete("/blocklist/{entry_id}", status_code=204)
def delete_blocklist(entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(BlocklistEntry, entry_id)
    if entry is None:
        raise HTTPException(404, "Blocklist entry not found")
    db.delete(entry)
    db.commit()


@router.post("/by-hash/{info_hash}/blocklist", response_model=dict)
async def blocklist_by_hash(info_hash: str, db: Session = Depends(get_db)):
    record = db.query(DownloadRecord).filter(DownloadRecord.info_hash == info_hash.lower(), DownloadRecord.status != "imported").order_by(DownloadRecord.id.desc()).first()
    if record is None:
        raise HTTPException(404, "No download record for that torrent")
    return await _blocklist_and_retry(db, record)


@router.post("/{download_id}/blocklist", response_model=dict)
async def blocklist_download(download_id: int, db: Session = Depends(get_db)):
    record = db.get(DownloadRecord, download_id)
    if record is None:
        raise HTTPException(404, "Download not found")
    return await _blocklist_and_retry(db, record)


def _entry_out(e) -> dict:
    return {"id": e.id, "info_hash": e.info_hash, "release_title": e.release_title, "reason": e.reason, "movie_id": e.movie_id, "episode_id": e.episode_id, "created_at": e.created_at.isoformat() if e.created_at else None, "expires_at": e.expires_at.isoformat() if e.expires_at else None}


async def _blocklist_and_retry(db: Session, record: DownloadRecord) -> dict:
    await fail_download(db, record, "blocklisted by hand")
    try:
        grabbed = await automation.retry_download(db, record)
    except Exception:
        grabbed = False
    return {"id": record.id, "status": record.status, "failure_reason": record.failure_reason, "searched_again": True, "grabbed": grabbed}


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
