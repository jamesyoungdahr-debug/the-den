"""Per-device sign-in tokens (M37): every app sign-in gets its own named token, stored only as a
SHA-256 hash, listed and revocable from the profile page; admins can revoke anyone's."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import DeviceToken, User

PLATFORMS = ("web", "kde", "android", "other")
NAME_MAX = 60
_TOUCH_EVERY = timedelta(minutes=5)


def new_token() -> str:
    return "den_" + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Tokens carry 256 random bits, so one SHA-256 pass is enough; no password-style stretching."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create(db: Session, user: User, name: str | None = None, platform: str | None = None) -> tuple[str, DeviceToken]:
    """Make a token for one device. Returns (plaintext, row); the plaintext is never stored."""
    token = new_token()
    clean_name = " ".join((name or "").split())[:NAME_MAX] or "Unnamed device"
    clean_platform = platform if platform in PLATFORMS else "other"
    row = DeviceToken(
        user_id=user.id, name=clean_name, platform=clean_platform, token_hash=hash_token(token),
        token_prefix=token[:8], created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return token, row


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def user_for_token(db: Session, token: str | None) -> User | None:
    """The account a token belongs to, or None. Records when it was last used, at most every few
    minutes, so a busy app doesn't write to the database on every request."""
    if not token:
        return None
    row = db.query(DeviceToken).filter(DeviceToken.token_hash == hash_token(token)).first()
    if row is None:
        return None
    now = datetime.now(timezone.utc)
    last = _aware(row.last_used_at)
    if last is None or now - last > _TOUCH_EVERY:
        row.last_used_at = now
        db.commit()
    return db.get(User, row.user_id)


def list_for(db: Session, user_id: int) -> list[DeviceToken]:
    return (
        db.query(DeviceToken).filter(DeviceToken.user_id == user_id)
        .order_by(DeviceToken.created_at.desc(), DeviceToken.id.desc()).all()
    )


def count_for(db: Session, user_id: int) -> int:
    return db.query(DeviceToken).filter(DeviceToken.user_id == user_id).count()


def revoke(db: Session, device_id: int, actor: User) -> bool:
    """Delete one device token if the actor owns it or is an admin. False when there is no such
    device the actor may touch, so a user can't probe other people's device ids."""
    row = db.get(DeviceToken, device_id)
    if row is None or (row.user_id != actor.id and not actor.is_admin):
        return False
    db.delete(row)
    db.commit()
    return True


def revoke_token(db: Session, token: str | None) -> bool:
    """Delete the token a request signed in with (an app signing out)."""
    if not token:
        return False
    deleted = db.query(DeviceToken).filter(DeviceToken.token_hash == hash_token(token)).delete()
    db.commit()
    return deleted > 0


def revoke_all(db: Session, user_id: int) -> int:
    deleted = db.query(DeviceToken).filter(DeviceToken.user_id == user_id).delete()
    db.commit()
    return deleted


def out(row: DeviceToken, current_token: str | None = None) -> dict:
    def iso(value: datetime | None) -> str | None:
        value = _aware(value)
        return value.isoformat() if value else None

    return {
        "id": row.id, "name": row.name, "platform": row.platform, "token_prefix": row.token_prefix,
        "created_at": iso(row.created_at), "last_used_at": iso(row.last_used_at),
        "current": bool(current_token) and row.token_hash == hash_token(current_token),
    }
