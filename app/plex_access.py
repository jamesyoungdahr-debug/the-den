"""Who may sign in with Plex, and how a Plex account becomes a Den user.

Policy (docs/requests-plan.md, "Users and auth"):
  * An account already linked to a Den user signs straight in.
  * On a fresh install (no users at all) the first Plex account becomes the owner: an
    admin, and its token is stored so the app can read the owner's server later.
  * Otherwise a Plex account gets in if it IS the owner, or the admin allowed any Plex
    account, or the owner shares the configured server with it. Everyone else is refused.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import plex
from app import settings as settings_module
from app.auth import users_exist
from app.models import User


def _unique_username(db: Session, wanted: str) -> str:
    base = (wanted or "plex").strip() or "plex"
    candidate, n = base, 2
    while db.query(User.id).filter(User.username == candidate).first() is not None:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def _refresh_from_plex(user: User, account: plex.Account) -> None:
    user.plex_username = account.username
    if account.email:
        user.email = account.email
    if account.thumb:
        user.avatar_url = account.thumb


def store_owner(db: Session, account: plex.Account, token: str) -> None:
    row = settings_module.get_row(db)
    row.plex_token = token
    row.plex_owner_id = account.id
    row.plex_owner_username = account.username
    db.commit()


async def is_allowed(db: Session, account: plex.Account) -> bool:
    s = settings_module.effective(db)
    if s.plex_owner_id and account.id == s.plex_owner_id:
        return True
    if s.plex_allow_any_account:
        return True
    if s.plex_token and s.plex_machine_id:
        try:
            return account.id in await plex.shared_user_ids(s.plex_token, s.plex_machine_id)
        except Exception:
            return False
    return False


async def user_for_account(db: Session, account: plex.Account, token: str) -> tuple[User | None, str | None]:
    """Find or create the Den user for a Plex account. Returns (user, None) or (None, reason)."""
    user = db.query(User).filter(User.plex_id == account.id).first()
    if user is not None:
        _refresh_from_plex(user, account)
        db.commit()
        return user, None

    if not users_exist(db):
        user = User(
            username=_unique_username(db, account.username), plex_id=account.id, role="admin", auto_approve=True,
            created_at=datetime.now(timezone.utc),
        )
        _refresh_from_plex(user, account)
        db.add(user)
        db.commit()
        store_owner(db, account, token)
        return user, None

    if not await is_allowed(db, account):
        return None, "That Plex account doesn't have access to this server. Ask the owner to share it with you."

    user = User(username=_unique_username(db, account.username), plex_id=account.id, role="user", created_at=datetime.now(timezone.utc))
    _refresh_from_plex(user, account)
    db.add(user)
    db.commit()
    return user, None


def link_account(db: Session, user: User, account: plex.Account) -> str | None:
    """Attach a Plex account to an existing (local) user. Returns an error message or None."""
    other = db.query(User).filter(User.plex_id == account.id, User.id != user.id).first()
    if other is not None:
        return f"That Plex account is already linked to {other.username}."
    user.plex_id = account.id
    _refresh_from_plex(user, account)
    db.commit()
    return None
