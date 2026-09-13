"""Database backup, a restore that is staged and swapped in at the next startup, and JSON exports (E10)."""

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.orm import Session

from app import config
from app.models import Indexer

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_TABLES = {"alembic_version", "settings", "users", "indexers"}


class BackupError(Exception):
    pass


def db_path() -> Path:
    prefix = "sqlite:///"
    if not config.DATABASE_URL.startswith(prefix):
        raise BackupError("Backup and restore only support SQLite databases.")
    return Path(config.DATABASE_URL[len(prefix):]).resolve()


def pending_path() -> Path:
    live = db_path()
    return live.with_name(live.name + ".restore-pending")


def current_head() -> str:
    return ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_current_head()


def snapshot(dest: Path) -> None:
    """A consistent copy of the live database, safe while the app keeps writing to it."""
    src = sqlite3.connect(db_path())
    try:
        out = sqlite3.connect(dest)
        try:
            src.backup(out)
        finally:
            out.close()
    finally:
        src.close()


def validate(path: Path) -> str:
    """Check an uploaded file is an intact The Den database at this install's schema; returns its revision."""
    with open(path, "rb") as f:
        if f.read(16) != b"SQLite format 3\x00":
            raise BackupError("That file isn't a SQLite database.")
    try:
        conn = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BackupError("That database failed its integrity check.")
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            missing = REQUIRED_TABLES - tables
            if missing:
                raise BackupError("That database isn't a The Den backup (missing tables: " + ", ".join(sorted(missing)) + ").")
            row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        finally:
            conn.close()
    except sqlite3.DatabaseError as e:
        raise BackupError(f"That database couldn't be read: {e}") from e
    revision = row[0] if row else None
    head = current_head()
    if revision != head:
        raise BackupError(f"That backup is at schema revision {revision}, but this install is at {head}. Only a backup from the same version can be restored.")
    return revision


def stage_restore(upload: Path) -> str:
    revision = validate(upload)
    target = pending_path()
    tmp = target.with_name(target.name + ".tmp")
    shutil.copyfile(upload, tmp)
    os.replace(tmp, target)
    return revision


def pending_restore() -> bool:
    try:
        return pending_path().exists()
    except BackupError:
        return False


def cancel_restore() -> bool:
    if not pending_restore():
        return False
    pending_path().unlink()
    return True


def apply_pending_restore() -> Path | None:
    """Swap a staged restore into place. Must run at startup, before anything opens the database.
    The previous database (and any rollback journal) is kept beside it as a .pre-restore copy."""
    if not pending_restore():
        return None
    live = db_path()
    kept = live.with_name(f"{live.name}.pre-restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    if live.exists():
        os.replace(live, kept)
    journal = live.with_name(live.name + "-journal")
    if journal.exists():
        os.replace(journal, kept.with_name(kept.name + "-journal"))
    os.replace(pending_path(), live)
    return kept


def indexers_export(db: Session) -> list[dict]:
    """The indexer list without API keys; has_api_key says which ones need a key re-entered."""
    return [
        {"name": i.name, "url": i.url, "protocol": i.protocol, "implementation": i.implementation, "preset": i.preset, "enabled": i.enabled, "has_api_key": bool(i.api_key)}
        for i in db.query(Indexer).order_by(Indexer.id).all()
    ]


def download_name(kind: str, ext: str) -> str:
    return f"the-den-{kind}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.{ext}"