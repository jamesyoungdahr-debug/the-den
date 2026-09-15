"""M51: a one-time link an admin hands somebody so they can set a Den password.

Plex sign-in is the only way some accounts have ever got in, and Plex is going away. Before it
can, those people need a password -- and the safe way to give them one is a link that expires and
works once, rather than an admin choosing a password on their behalf and reading it out.

Only the hash is ever stored, exactly as device tokens are: the raw token exists once, in the URL
the admin copies, and never again. A dump of the database is therefore not a set of working links
to every account.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import User

LINK_DAYS = 7
MIN_PASSWORD = 8
_TOKEN_PREFIX = "denjoin_"


def new_token() -> str:
    """A link token. The prefix makes one recognisable in a log or a bug report without being
    worth anything on its own."""
    return _TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """256 random bits, so one SHA-256 pass is enough; no password-style stretching needed."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _aware(value: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; everything here is compared in UTC."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def create(db: Session, user: User) -> str:
    """Mint a link for this user and return the raw token, the only moment it is readable.

    A user holds one link at a time, so minting a second quietly retires the first -- which is
    what an admin wants when a link has gone astray."""
    token = new_token()
    user.sign_in_token_hash = hash_token(token)
    user.sign_in_expires_at = datetime.now(timezone.utc) + timedelta(days=LINK_DAYS)
    db.commit()
    return token


def user_for_token(db: Session, token: str | None) -> User | None:
    """The account a link belongs to while it is still valid, or None.

    This does not consume the link: the page has to render its form, and possibly be reloaded,
    before a password is actually set."""
    if not token:
        return None
    user = db.query(User).filter(User.sign_in_token_hash == hash_token(token)).first()
    if user is None:
        return None
    expires = _aware(user.sign_in_expires_at)
    if expires is None or expires < datetime.now(timezone.utc):
        return None
    return user


def redeem(db: Session, token: str | None, password: str) -> User | None:
    """Set the password and burn the link, so it cannot be used again.

    Returns None for an unusable link, an expired one, or a password under MIN_PASSWORD. The
    caller deliberately cannot tell those apart from the outside, so probing a token teaches a
    stranger nothing about whether an account exists."""
    user = user_for_token(db, token)
    if user is None or len(password) < MIN_PASSWORD:
        return None
    # Local import: app/auth.py is the module that knows how passwords are hashed, and importing
    # it at module level would tie this file's import order to it for no benefit.
    from app import auth

    user.password_hash = auth.hash_password(password)
    user.sign_in_token_hash = None
    user.sign_in_expires_at = None
    db.commit()
    return user


def clear(db: Session, user: User) -> None:
    """Revoke any outstanding link for a user, without setting a password."""
    user.sign_in_token_hash = None
    user.sign_in_expires_at = None
    db.commit()
