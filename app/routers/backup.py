"""Settings -> Backup (E10): database download, JSON exports, and a staged restore. Web only, admin only."""

import os
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app import auth, backup
from app.deps import get_db
from app.routers.api_settings import get_settings

router = APIRouter(tags=["backup"], dependencies=[Depends(auth.page_admin)])


def _back(kind: str, message: str) -> RedirectResponse:
    return RedirectResponse(f"/ui/settings?{kind}={quote(message)}#backup", status_code=303)


def _attachment(name: str) -> dict:
    return {"Content-Disposition": f'attachment; filename="{name}"'}


@router.get("/ui/backup/database")
def download_database():
    fd, name = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    tmp = Path(name)
    try:
        backup.snapshot(tmp)
    except (backup.BackupError, OSError, sqlite3.Error) as e:
        tmp.unlink(missing_ok=True)
        return _back("error", f"Backup failed: {e}")
    return FileResponse(tmp, media_type="application/vnd.sqlite3", filename=backup.download_name("backup", "db"), background=BackgroundTask(tmp.unlink, missing_ok=True))


@router.get("/ui/backup/settings.json")
def export_settings(db: Session = Depends(get_db)):
    return JSONResponse(get_settings(db), headers=_attachment(backup.download_name("settings", "json")))


@router.get("/ui/backup/indexers.json")
def export_indexers(db: Session = Depends(get_db)):
    return JSONResponse(backup.indexers_export(db), headers=_attachment(backup.download_name("indexers", "json")))


@router.post("/ui/backup/restore")
async def stage_restore(file: UploadFile = File(...), confirm: str = Form("")):
    if confirm != "yes":
        return _back("error", "Tick the confirmation box to stage a restore.")
    try:
        target_dir = backup.db_path().parent
    except backup.BackupError as e:
        return _back("error", str(e))
    fd, name = tempfile.mkstemp(suffix=".upload", dir=target_dir)
    os.close(fd)
    tmp = Path(name)
    try:
        with open(tmp, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                out.write(chunk)
        revision = backup.stage_restore(tmp)
    except backup.BackupError as e:
        return _back("error", str(e))
    except OSError as e:
        return _back("error", f"Couldn't stage the restore: {e}")
    finally:
        tmp.unlink(missing_ok=True)
    return _back("notice", f"Restore staged (schema {revision}). Restart The Den to swap it in; the current database is kept beside it as a .pre-restore copy.")


@router.post("/ui/backup/restore/cancel")
def cancel_restore():
    return _back("notice", "Staged restore cancelled." if backup.cancel_restore() else "There was no staged restore to cancel.")
