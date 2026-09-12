"""Discover (U4): TMDB rails and search from /api/discover/*, and the detail record for
one movie or series with its availability (library + Plex) and request state."""

from __future__ import annotations

from PySide6.QtCore import Property, QUrl, Signal, Slot

from models.base import JsonListModel, JsonRecord

CARD_FIELDS = [
    ("mediaType", "media_type"),
    ("tmdbId", "tmdb_id"),
    ("title", "title"),
    ("year", "year"),
    ("overview", "overview", ""),
    ("posterPath", "poster_path", ""),
    ("backdropPath", "backdrop_path", ""),
    ("rating", "rating", 0.0),
    ("status", "status", ""),
    ("onPlex", "on_plex", False),
    ("libraryHref", "library_href", ""),
]


class RailModel(JsonListModel):
    """One Discover rail -- GET /api/discover/{rail}: trending, popular-movies,
    upcoming-movies, popular-tv, on-the-air, recommended."""

    FIELDS = CARD_FIELDS

    def __init__(self, api, rail: str, parent=None):
        super().__init__(api, parent)
        self._rail = rail

    rail = Property(str, lambda self: self._rail, constant=True)

    @Slot()
    def refresh(self) -> None:
        self._fetch(f"/api/discover/{self._rail}")


class DiscoverSearchModel(JsonListModel):
    """GET /api/discover/search?q= -- movies and series together, each card stamped
    with the library's / Plex's status."""

    FIELDS = CARD_FIELDS
    queryChanged = Signal()

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._query = ""

    query = Property(str, lambda self: self._query, notify=queryChanged)

    @Slot(str)
    def search(self, query: str) -> None:
        self._query = query.strip()
        self.queryChanged.emit()
        if not self._query:
            self._set_items([])
            return
        self._fetch(f"/api/discover/search?q={QUrl.toPercentEncoding(self._query).data().decode()}")


class DetailController(JsonRecord):
    """GET /api/discover/movie|tv/{id}: everything the detail page shows, and the
    actions on it. Requesting goes through POST /api/requests -- for admins the backend
    approves instantly and that is how "Add to library" works from here too."""

    requestFinished = Signal(bool, str)
    kindChanged = Signal()

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._kind = ""
        self._tmdb_id = 0

    kind = Property(str, lambda self: self._kind, notify=kindChanged)
    tmdbId = Property(int, lambda self: self._tmdb_id, notify=kindChanged)

    @Slot(str, int)
    def load(self, kind: str, tmdbId: int) -> None:
        self._kind, self._tmdb_id = kind, tmdbId
        self.kindChanged.emit()
        self._set_data({})
        self._fetch(f"/api/discover/{kind}/{tmdbId}")

    @Slot()
    def reload(self) -> None:
        if self._kind:
            self._fetch(f"/api/discover/{self._kind}/{self._tmdb_id}")

    @Slot(list)
    def request(self, seasons: list) -> None:
        payload: dict = {"media_type": self._kind, "tmdb_id": self._tmdb_id}
        if self._kind == "tv" and seasons:
            payload["seasons"] = [int(s) for s in seasons]

        def on_done(status: int, body) -> None:
            if status == 201 and isinstance(body, dict):
                approved = body.get("status") == "approved"
                self.requestFinished.emit(True, "Added to the library" if approved else "Request sent for approval")
                self.reload()
            else:
                self.requestFinished.emit(False, self.api.error_message(status, body))

        self.api.request("POST", "/api/requests", payload, on_done)
