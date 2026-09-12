"""Health checks (M16): folders, torrent engine, Cloudflare solver, Plex sign-in, failing indexers.
Runs at the end of every automation cycle; open issues live in health_issues and new ones fire
a health_warning notification."""

import os
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app import plex
from app import settings as settings_module
from app.indexers import catalog, solver
from app.indexers.native import NATIVES
from app.models import HealthIssue, Indexer, IndexerStat
from app.notifier import notify_event
from app.torrent import engine

Issue = tuple[str, str, str]  # key, level, message


def _folder_issue(key: str, label: str, path: str) -> Issue | None:
    if not path or not os.path.isdir(path):
        return (key, "error", f"{label} folder {path!r} does not exist")
    if not os.access(path, os.W_OK):
        return (key, "error", f"{label} folder {path!r} is not writable")
    return None


def _needs_solver(ix: Indexer) -> bool:
    if ix.implementation in NATIVES and NATIVES[ix.implementation].cloudflare:
        return True
    return bool(ix.preset) and ix.preset in catalog.BY_SLUG and catalog.BY_SLUG[ix.preset].cloudflare


async def collect(db: Session) -> list[Issue]:
    """Every problem we can detect right now, as (key, level, message)."""
    s = settings_module.effective(db)
    issues: list[Issue] = []

    for key, label, path in (("movies_root", "Movies", s.movies_root), ("tv_root", "TV", s.tv_root), ("downloads_root", "Downloads", s.downloads_root)):
        issue = _folder_issue(key, label, path)
        if issue:
            issues.append(issue)

    if not engine.info().get("running"):
        issues.append(("torrent_engine", "error", "The built-in torrent client is not running"))

    enabled = db.query(Indexer).filter(Indexer.enabled == True).all()  # noqa: E712
    if any(_needs_solver(ix) for ix in enabled) and not s.flaresolverr_url and not solver.available():
        issues.append(("solver", "warning", "An enabled indexer needs a Cloudflare solver, but no Chromium was found and no FlareSolverr/Byparr URL is set"))

    if s.plex_token:
        try:
            await plex.get_account(s.plex_token)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                issues.append(("plex_token", "error", "The Plex sign-in has expired; sign in again from Settings"))
            else:
                issues.append(("plex_unreachable", "warning", f"plex.tv could not be reached: {exc}"))
        except Exception as exc:
            issues.append(("plex_unreachable", "warning", f"plex.tv could not be reached: {exc}"))

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for ix in enabled:
        stat = db.query(IndexerStat).filter(IndexerStat.indexer_id == ix.id, IndexerStat.day == today).first()
        if stat and stat.searches >= 3 and stat.successes == 0:
            issues.append((f"indexer_{ix.id}", "warning", f"Indexer {ix.name} failed every search today" + (f": {stat.last_error}" if stat.last_error else "")))

    return issues


async def run(db: Session) -> list[HealthIssue]:
    """Re-check, reconcile the health_issues table, notify about anything new."""
    s = settings_module.effective(db)
    collected = await collect(db)
    now = datetime.now(timezone.utc)
    existing = {row.key: row for row in db.query(HealthIssue).all()}
    new_issues: list[HealthIssue] = []

    for key, level, message in collected:
        row = existing.get(key)
        if row:
            row.level, row.message, row.last_seen = level, message, now
        else:
            row = HealthIssue(key=key, level=level, message=message, first_seen=now, last_seen=now)
            db.add(row)
            new_issues.append(row)
    keys = {c[0] for c in collected}
    for key, row in existing.items():
        if key not in keys:
            db.delete(row)
    db.commit()

    for issue in new_issues:
        try:
            await notify_event(db, "health_warning", issue.message, legacy_discord_url=s.discord_webhook_url)
        except Exception:
            pass

    return db.query(HealthIssue).order_by(HealthIssue.first_seen).all()


def current(db: Session) -> list[dict]:
    """The open issues as plain dicts for /health and the pages."""
    return [
        {"key": i.key, "level": i.level, "message": i.message, "first_seen": i.first_seen.isoformat(), "last_seen": i.last_seen.isoformat()}
        for i in db.query(HealthIssue).order_by(HealthIssue.first_seen).all()
    ]
