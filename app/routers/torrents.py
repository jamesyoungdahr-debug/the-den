"""JSON API over the built-in torrent client: everything the Downloads page (and the
companion apps) need to show live progress and drive pause/resume/remove, plus a
way to add a torrent by hand that isn't tied to any movie or episode."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth
from app import settings as settings_module
from app.deps import get_db
from app.models import DownloadRecord, Episode, Movie, Series
from app.torrent import TorrentStatus, engine
from app.parser import parse_quality
from app import history

router = APIRouter(prefix="/torrents", tags=["torrents"], dependencies=[Depends(auth.require_admin)])


class TorrentOut(BaseModel):
    info_hash: str
    name: str
    state: str
    progress: float
    total_size: int
    downloaded: int
    uploaded: int
    download_rate: int
    upload_rate: int
    num_peers: int
    num_seeds: int
    eta_seconds: int | None
    ratio: float
    is_finished: bool
    save_path: str
    error: str | None
    added_at: int
    # What this torrent is for, if The Den grabbed it for something in the library.
    record_id: int | None = None
    record_status: str | None = None
    movie_id: int | None = None
    episode_id: int | None = None
    label: str | None = None


class TorrentAdd(BaseModel):
    source: str  # magnet link, URL to a .torrent, or a local .torrent path


def _decorate(db: Session, statuses: list[TorrentStatus]) -> list[TorrentOut]:
    hashes = [s.info_hash for s in statuses]
    records: dict[str, DownloadRecord] = {}
    if hashes:
        # Newest record wins if a hash was grabbed more than once.
        for record in db.query(DownloadRecord).filter(DownloadRecord.info_hash.in_(hashes)).order_by(DownloadRecord.id):
            records[record.info_hash] = record

    movie_ids = {r.movie_id for r in records.values() if r.movie_id}
    episode_ids = {r.episode_id for r in records.values() if r.episode_id}
    movies = {m.id: m for m in db.query(Movie).filter(Movie.id.in_(movie_ids))} if movie_ids else {}
    episodes = {e.id: e for e in db.query(Episode).filter(Episode.id.in_(episode_ids))} if episode_ids else {}
    series_ids = {e.series_id for e in episodes.values()}
    series = {s.id: s for s in db.query(Series).filter(Series.id.in_(series_ids))} if series_ids else {}

    out = []
    for st in statuses:
        item = TorrentOut(**st.__dict__)
        record = records.get(st.info_hash)
        if record is not None:
            item.record_id = record.id
            item.record_status = record.status
            item.movie_id = record.movie_id
            item.episode_id = record.episode_id
            if record.movie_id and record.movie_id in movies:
                m = movies[record.movie_id]
                item.label = f"{m.title} ({m.year})" if m.year else m.title
            elif record.episode_id and record.episode_id in episodes:
                e = episodes[record.episode_id]
                show = series.get(e.series_id)
                item.label = f"{show.title if show else '?'} S{e.season_number:02d}E{e.episode_number:02d}"
        out.append(item)
    return out


@router.get("", response_model=list[TorrentOut])
def list_torrents(db: Session = Depends(get_db)):
    return _decorate(db, engine.list())


@router.get("/engine")
def engine_info():
    return engine.info()


@router.post("", response_model=TorrentOut, status_code=201)
async def add_torrent(payload: TorrentAdd, db: Session = Depends(get_db)):
    source = payload.source.strip()
    if not source:
        raise HTTPException(400, "source is required")
    try:
        key = await engine.add(source, save_path=settings_module.effective(db).downloads_root)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"could not fetch torrent: {exc}")
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    name = engine.status(key).name if engine.status(key) else source
    db.add(DownloadRecord(download_url=source, info_hash=key, release_title=name, status="queued", quality=parse_quality(name)))
    db.commit()
    st = engine.status(key)
    if st is None:
        raise HTTPException(500, "torrent was added but is not visible")
    return _decorate(db, [st])[0]


@router.get("/{info_hash}", response_model=TorrentOut)
def get_torrent(info_hash: str, db: Session = Depends(get_db)):
    st = engine.status(info_hash)
    if st is None:
        raise HTTPException(404, "Torrent not found")
    return _decorate(db, [st])[0]


@router.post("/{info_hash}/pause", status_code=204)
def pause_torrent(info_hash: str):
    try:
        engine.pause(info_hash)
    except KeyError:
        raise HTTPException(404, "Torrent not found")


@router.post("/{info_hash}/resume", status_code=204)
def resume_torrent(info_hash: str):
    try:
        engine.resume(info_hash)
    except KeyError:
        raise HTTPException(404, "Torrent not found")


@router.delete("/{info_hash}", status_code=204)
def remove_torrent(info_hash: str, delete_files: bool = False, db: Session = Depends(get_db)):
    if engine.status(info_hash) is None:
        raise HTTPException(404, "Torrent not found")
    titled = db.query(DownloadRecord).filter(DownloadRecord.info_hash == info_hash).order_by(DownloadRecord.id.desc()).first()
    if titled and (titled.movie_id or titled.episode_id or titled.series_id):
        history.record(db, "removed", titled.release_title, movie_id=titled.movie_id, episode_id=titled.episode_id, series_id=titled.series_id, season_number=titled.season_number, message="removed by hand" + (" (files deleted)" if delete_files else ""))
    engine.remove(info_hash, delete_files=delete_files)
    # Any record still waiting on it can't finish now; say so instead of leaving it
    # "downloading" until the next automation cycle notices the torrent is gone.
    db.query(DownloadRecord).filter(
        DownloadRecord.info_hash == info_hash,
        DownloadRecord.status.notin_(["imported", "failed"]),
    ).update({"status": "failed"})
    db.commit()
