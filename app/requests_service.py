"""Requests (M11f): a user asks for a movie or for seasons of a series; an admin approves
or declines; approval drops the title straight into the library, which the automation
loop then fetches. Availability is derived from the library and the Plex scan every time
it's asked for; once an approved request is found fulfilled it is stamped "available"
(M11g) so the requester is told exactly once. Non-admins have request quotas (M11g)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import plex_scan, tmdb, tvmaze
from app import settings as settings_module
from app.models import Episode, MediaRequest, Movie, Series, User
from app.notifier import notify_event

OPEN_STATUSES = ("pending", "approved")


class RequestError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# ---- availability -------------------------------------------------------------------

def availability(db: Session, media_type: str, tmdb_id: int, tvdb_id: int | None = None) -> dict:
    """What we have for a title: den (library rows) and plex (scan rows)."""
    plex_movies, plex_tv_tmdb, plex_tv_tvdb = plex_scan.plex_index(db)
    out: dict = {"den": None, "plex": None, "available_seasons": set(), "partial": False, "available": False}
    if media_type == "movie":
        m = db.query(Movie).filter(Movie.tmdb_id == tmdb_id).first()
        p = plex_movies.get(tmdb_id)
        out["den"] = {"id": m.id, "has_file": m.has_file} if m else None
        out["plex"] = {"title": p.title, "year": p.year} if p else None
        out["available"] = bool((m and m.has_file) or p)
        return out
    s = db.query(Series).filter(Series.tmdb_id == tmdb_id).first()
    p = plex_tv_tmdb.get(tmdb_id) or (plex_tv_tvdb.get(tvdb_id) if tvdb_id else None)
    den_seasons: dict[int, dict] = {}
    if s:
        for e in db.query(Episode).filter(Episode.series_id == s.id):
            row = den_seasons.setdefault(e.season_number, {"have": 0, "total": 0, "monitored": False})
            row["total"] += 1
            row["have"] += 1 if e.has_file else 0
            row["monitored"] = row["monitored"] or e.monitored
        out["den"] = {"id": s.id, "seasons": den_seasons, "have": sum(r["have"] for r in den_seasons.values()), "total": sum(r["total"] for r in den_seasons.values())}
    plex_seasons = plex_scan.season_counts(p)
    if p:
        out["plex"] = {"title": p.title, "year": p.year, "seasons": plex_seasons}
    complete = {n for n, r in den_seasons.items() if r["total"] and r["have"] == r["total"]}
    complete |= {n for n, c in plex_seasons.items() if c > 0}
    out["available_seasons"] = complete
    out["partial"] = bool(complete) or any(r["have"] for r in den_seasons.values())
    return out


def open_requests_for(db: Session, media_type: str, tmdb_id: int) -> list[MediaRequest]:
    return db.query(MediaRequest).filter(
        MediaRequest.media_type == media_type, MediaRequest.tmdb_id == tmdb_id, MediaRequest.status.in_(OPEN_STATUSES)
    ).all()


def fulfilled(db: Session, req: MediaRequest) -> bool:
    """An approved request whose title (or every requested season) is now available."""
    if req.status == "available":
        return True
    if req.status != "approved":
        return False
    av = availability(db, req.media_type, req.tmdb_id)
    if req.media_type == "movie":
        return av["available"]
    wanted = set(req.season_list)
    if not wanted:  # whole series: every season the library knows about
        den = av["den"] or {}
        seasons = den.get("seasons") or {}
        return bool(seasons) and all(r["total"] and r["have"] == r["total"] for r in seasons.values())
    return wanted <= av["available_seasons"]


async def mark_available(db: Session) -> list[MediaRequest]:
    """Stamp approved requests that are now fulfilled (library import or Plex scan) and
    tell the channel once. Called at the end of every automation cycle and Plex scan."""
    done: list[MediaRequest] = []
    for req in db.query(MediaRequest).filter(MediaRequest.status == "approved").all():
        if fulfilled(db, req):
            req.status = "available"
            req.available_at = datetime.now(timezone.utc)
            done.append(req)
    if done:
        db.commit()
        s = settings_module.effective(db)
        for req in done:
            requester = db.get(User, req.requested_by)
            await notify_event(db, "request_available", f"**{_label(req)}** is now available" + (f" -- requested by {requester.username}" if requester else ""), legacy_discord_url=s.discord_webhook_url, link=f"theden://detail/{req.media_type}/{req.tmdb_id}")
    return done


# ---- quotas ------------------------------------------------------------------------------

def quota(db: Session, user: User) -> dict:
    """Requests made by this user in the current window against their limits. Admins are
    exempt (limit None). Per-user limits override the Settings defaults; 0 = unlimited."""
    s = settings_module.effective(db)
    days = user.limit_days or s.request_limit_days
    limits = {
        "movie": s.request_movie_limit if user.movie_limit is None else user.movie_limit,
        "tv": s.request_series_limit if user.series_limit is None else user.series_limit,
    }
    since = datetime.now(timezone.utc) - timedelta(days=days)
    out = {"days": days, "exempt": user.is_admin}
    for kind, key in (("movie", "movies"), ("tv", "series")):
        used = db.query(MediaRequest).filter(
            MediaRequest.requested_by == user.id, MediaRequest.media_type == kind,
            MediaRequest.status != "declined", MediaRequest.created_at >= since,
        ).count()
        limit = None if user.is_admin or not limits[kind] else limits[kind]
        out[key] = {"used": used, "limit": limit, "remaining": None if limit is None else max(0, limit - used)}
    return out


def _check_quota(db: Session, user: User, media_type: str) -> None:
    q = quota(db, user)
    bucket = q["movies" if media_type == "movie" else "series"]
    if bucket["limit"] is not None and bucket["remaining"] <= 0:
        what = "movies" if media_type == "movie" else "series"
        raise RequestError(429, f"Request limit reached: {bucket['limit']} {what} every {q['days']} days")


# ---- create ----------------------------------------------------------------------------

async def create_request(db: Session, user: User, media_type: str, tmdb_id: int, seasons: list[int] | None) -> MediaRequest:
    if media_type not in ("movie", "tv"):
        raise RequestError(400, "media_type must be movie or tv")
    s = settings_module.effective(db)
    details = await (tmdb.movie_details if media_type == "movie" else tmdb.tv_details)(tmdb_id, s.tmdb_api_key)
    if details is None:
        raise RequestError(404, "That title isn't on TMDB")

    av = availability(db, media_type, tmdb_id, details.get("tvdb_id"))
    seasons = sorted({int(n) for n in (seasons or []) if int(n) > 0})
    if media_type == "movie":
        if av["available"]:
            raise RequestError(409, "Already available" + (" on Plex" if av["plex"] else " in the library"))
        if av["den"]:
            raise RequestError(409, "Already in the library and being looked for")
    else:
        all_seasons = [x["season_number"] for x in details.get("seasons", []) if x["season_number"] > 0]
        if not seasons:
            seasons = all_seasons
        unknown = [n for n in seasons if n not in all_seasons]
        if unknown:
            raise RequestError(400, f"No such season: {', '.join(map(str, unknown))}")
        seasons = [n for n in seasons if n not in av["available_seasons"]]
        if not seasons:
            raise RequestError(409, "Every requested season is already available")
        den = av["den"]
        if den:
            already_wanted = {n for n, r in den["seasons"].items() if r["monitored"] and r["have"] < r["total"]}
            seasons = [n for n in seasons if n not in already_wanted]
            if not seasons:
                raise RequestError(409, "Those seasons are already in the library and being looked for")

    for existing in open_requests_for(db, media_type, tmdb_id):
        if media_type == "movie" or not existing.season_list or set(existing.season_list) & set(seasons):
            who = "you" if existing.requested_by == user.id else "someone"
            raise RequestError(409, f"Already requested by {who} ({existing.status})")
    _check_quota(db, user, media_type)

    req = MediaRequest(
        media_type=media_type, tmdb_id=tmdb_id, title=details["title"], year=details.get("year"),
        poster_path=details.get("poster_path"), seasons=json.dumps(seasons) if media_type == "tv" else None,
        status="pending", requested_by=user.id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    if user.is_admin or user.auto_approve:
        await approve(db, req, user)
    else:
        await notify_event(db, "request_submitted", f"**{user.username}** requested **{_label(req)}** -- approve it at /requests", legacy_discord_url=s.discord_webhook_url, link=f"theden://requests/{req.id}")
    return req


def _label(req: MediaRequest) -> str:
    label = f"{req.title} ({req.year})" if req.year else req.title
    if req.media_type == "tv" and req.season_list:
        label += " " + ", ".join(f"S{n:02d}" for n in req.season_list)
    return label


# ---- decide ----------------------------------------------------------------------------

async def approve(db: Session, req: MediaRequest, admin: User) -> MediaRequest:
    if req.status == "approved":
        return req
    s = settings_module.effective(db)
    if req.media_type == "movie":
        movie = db.query(Movie).filter(Movie.tmdb_id == req.tmdb_id).first()
        if movie is None:
            details = await tmdb.movie_details(req.tmdb_id, s.tmdb_api_key) or {}
            movie = Movie(
                tmdb_id=req.tmdb_id, title=req.title, year=req.year,
                overview=details.get("overview"), poster_path=req.poster_path or details.get("poster_path"),
            )
            db.add(movie)
            db.flush()
        req.movie_id = movie.id
    else:
        series = db.query(Series).filter(Series.tmdb_id == req.tmdb_id).first()
        if series is None:
            details = await tmdb.tv_details(req.tmdb_id, s.tmdb_api_key)
            if details is None:
                raise RequestError(404, "That series isn't on TMDB any more")
            show = await _map_tv(details)
            if show is None:
                raise RequestError(502, "Couldn't match this series on TVmaze (which supplies episode lists). Add it from the TV page by name, then approve again.")
            series = db.query(Series).filter(Series.tvmaze_id == show["tvmaze_id"]).first()
            if series is None:
                series = Series(
                    tvmaze_id=show["tvmaze_id"], tmdb_id=req.tmdb_id, title=details["title"], year=details.get("year") or show["year"],
                    overview=details.get("overview") or show["overview"], poster_path=details.get("poster_path") or show["poster_path"],
                )
                db.add(series)
                db.flush()
                wanted = set(req.season_list)
                for ep in await tvmaze.get_tv_episodes(show["tvmaze_id"]):
                    db.add(Episode(series_id=series.id, monitored=(not wanted or ep["season_number"] in wanted), **ep))
            else:
                series.tmdb_id = req.tmdb_id
        wanted = set(req.season_list)
        if wanted:
            db.query(Episode).filter(Episode.series_id == series.id, Episode.season_number.in_(wanted)).update({"monitored": True}, synchronize_session=False)
        else:
            db.query(Episode).filter(Episode.series_id == series.id).update({"monitored": True}, synchronize_session=False)
        req.series_id = series.id
    req.status = "approved"
    req.decided_by = admin.id
    req.decided_at = datetime.now(timezone.utc)
    db.commit()
    requester = db.get(User, req.requested_by)
    await notify_event(db, "request_approved", f"Approved **{_label(req)}** for {requester.username if requester else 'someone'} -- The Den is looking for it", legacy_discord_url=s.discord_webhook_url, link=f"theden://requests/{req.id}")
    return req


async def _map_tv(details: dict) -> dict | None:
    show = None
    if details.get("tvdb_id"):
        show = await tvmaze.lookup_show(thetvdb=details["tvdb_id"])
    if show is None and details.get("imdb_id"):
        show = await tvmaze.lookup_show(imdb=details["imdb_id"])
    if show is None:
        show = await tvmaze.find_show(details["title"], details.get("year"))
    return show


async def decline(db: Session, req: MediaRequest, admin: User, note: str | None = None) -> MediaRequest:
    req.status = "declined"
    req.decided_by = admin.id
    req.decided_at = datetime.now(timezone.utc)
    if note:
        req.note = note.strip()[:300]
    db.commit()
    s = settings_module.effective(db)
    requester = db.get(User, req.requested_by)
    await notify_event(db, "request_declined", f"Declined **{_label(req)}** for {requester.username if requester else 'someone'}" + (f": {req.note}" if req.note else ""), legacy_discord_url=s.discord_webhook_url, link=f"theden://requests/{req.id}")
    return req


def label(req: MediaRequest) -> str:
    return _label(req)
