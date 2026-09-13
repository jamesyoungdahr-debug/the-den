"""E2: root folders -- named library folders per media type (Kids Movies vs Movies, 4K vs
1080p, etc.), resolved the same way app/candidates.py's profile_for() resolves a quality
profile: the title's own folder, else the media type's marked default, else the caller's
fallback (Settings.movies_root/tv_root)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import RootFolder


def root_folder_for(db: Session, root_folder_id: int | None, media_type: str, fallback_path: str) -> str:
    """The path a title should import into: its own root folder, else the default one
    marked for `media_type` ("movie" or "tv"), else `fallback_path`."""
    if root_folder_id:
        rf = db.get(RootFolder, root_folder_id)
        if rf:
            return rf.path
    default = db.query(RootFolder).filter(RootFolder.media_type == media_type, RootFolder.is_default == True).first()  # noqa: E712
    return default.path if default else fallback_path
