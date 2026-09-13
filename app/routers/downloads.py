import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import auth, automation, blocklist, importer, settings as settings_module
from app.deps import get_db
from app.download_check import check_and_import, fail_download
from app.models import DownloadRecord, BlocklistEntry, Episode, Movie, Series
from app.schemas import AssignBody, DownloadRecordOut, ImportAsIsBody, SeasonEpisodeOut, UnmatchedDownloadOut, UnmatchedFileOut
from app.torrent import engine

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


def _unmatched_entry(db: Session, r: DownloadRecord) -> UnmatchedDownloadOut | None:
    """Builds one queue entry for a download with leftover files: its file list (with
    live sizes read from the engine when the torrent is still there), what kind of gap
    it is, a human label, and -- for a season pack -- the season's episodes to pick from.
    Returns None when there is nothing left to show (the JSON list came back empty)."""
    names = json.loads(r.unmatched_files or "[]")
    sizes = {}
    if r.info_hash:
        try:
            sizes = {f.path.split("/")[-1].split("\\")[-1]: f.size for f in engine.files(r.info_hash)}
        except Exception:
            sizes = {}
    files = [UnmatchedFileOut(name=n, size=sizes.get(n, 0)) for n in names]
    if not files:
        return None
    kind, label, season_episodes = "manual", r.release_title, []
    if r.movie_id and (movie := db.get(Movie, r.movie_id)):
        kind = "movie"
        label = f"{movie.title} ({movie.year})" if movie.year else movie.title
    elif r.episode_id and (episode := db.get(Episode, r.episode_id)):
        kind = "episode"
        series = db.get(Series, episode.series_id)
        label = f"{series.title if series else '?'} S{episode.season_number:02d}E{episode.episode_number:02d}"
    elif r.series_id and r.season_number is not None and (series := db.get(Series, r.series_id)):
        kind = "season"
        label = f"{series.title} Season {r.season_number}"
        season_episodes = [
            SeasonEpisodeOut(id=e.id, label=f"S{e.season_number:02d}E{e.episode_number:02d}" + (f" - {e.title}" if e.title else ""))
            for e in db.query(Episode).filter(Episode.series_id == series.id, Episode.season_number == r.season_number).order_by(Episode.episode_number).all()
        ]
    return UnmatchedDownloadOut(
        id=r.id, release_title=r.release_title, status=r.status, failure_reason=r.failure_reason,
        kind=kind, label=label, movie_id=r.movie_id, episode_id=r.episode_id, series_id=r.series_id,
        season_number=r.season_number, files=files, season_episodes=season_episodes,
    )


@router.get("/unmatched", response_model=list[UnmatchedDownloadOut])
def list_unmatched(db: Session = Depends(get_db)):
    """Every download with leftover files an admin needs to place by hand: a movie or
    episode grab that found no video, a season pack with files left over, or a torrent
    added by hand that was never tied to a title."""
    records = db.query(DownloadRecord).filter(DownloadRecord.unmatched_files.isnot(None)).all()
    return [e for r in records if (e := _unmatched_entry(db, r)) is not None]


@router.post("/{download_id}/assign", response_model=DownloadRecordOut)
def assign_download(download_id: int, body: AssignBody, db: Session = Depends(get_db)):
    """Link one leftover file from a download to a movie or episode by hand, with the
    normal Plex naming, and drop it from the unmatched list."""
    record = db.get(DownloadRecord, download_id)
    if record is None or not record.info_hash:
        raise HTTPException(404, "Download not found")
    names = json.loads(record.unmatched_files or "[]")
    if body.file not in names:
        raise HTTPException(400, "That file isn't in this download's unmatched list")
    s = settings_module.effective(db)
    files = engine.files(record.info_hash)
    if body.kind == "movie":
        movie = db.get(Movie, body.id)
        if movie is None:
            raise HTTPException(404, "Movie not found")
        dest = importer.import_movie(files, movie, s.movies_root, source_name=body.file)
        if dest is None:
            raise HTTPException(400, "Couldn't link that file")
        movie.has_file = True
        movie.file_quality = record.quality
        movie.file_score = record.score or 0
        movie.file_path = str(dest)
        record.movie_id = movie.id
    elif body.kind == "episode":
        episode = db.get(Episode, body.id)
        if episode is None:
            raise HTTPException(404, "Episode not found")
        series = db.get(Series, episode.series_id)
        dest = importer.import_episode(files, series, episode, s.tv_root, source_name=body.file)
        if dest is None:
            raise HTTPException(400, "Couldn't link that file")
        episode.has_file = True
        episode.file_quality = record.quality
        episode.file_score = record.score or 0
        episode.file_path = str(dest)
        record.episode_id = episode.id
    else:
        raise HTTPException(400, "kind must be 'movie' or 'episode'")
    names.remove(body.file)
    record.unmatched_files = json.dumps(names) if names else None
    if not names:
        record.status = "imported"
        record.failure_reason = None
    db.commit()
    db.refresh(record)
    return record


@router.post("/{download_id}/import-as-is", response_model=DownloadRecordOut)
def import_as_is(download_id: int, body: ImportAsIsBody, db: Session = Depends(get_db)):
    """Link one leftover file straight into the library root under its original name, no
    title match. For files the admin wants kept but won't tie to a specific title yet."""
    record = db.get(DownloadRecord, download_id)
    if record is None or not record.info_hash:
        raise HTTPException(404, "Download not found")
    names = json.loads(record.unmatched_files or "[]")
    if body.file not in names:
        raise HTTPException(400, "That file isn't in this download's unmatched list")
    if body.root not in ("movies", "tv"):
        raise HTTPException(400, "root must be 'movies' or 'tv'")
    s = settings_module.effective(db)
    dest_root = s.movies_root if body.root == "movies" else s.tv_root
    dest = importer.import_as_is(engine.files(record.info_hash), body.file, dest_root)
    if dest is None:
        raise HTTPException(400, "Couldn't link that file")
    names.remove(body.file)
    record.unmatched_files = json.dumps(names) if names else None
    db.commit()
    db.refresh(record)
    return record
