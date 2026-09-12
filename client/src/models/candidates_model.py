from PySide6.QtCore import Property, Signal, Slot

from models.base import JsonListModel


class CandidatesModel(JsonListModel):
    """Scored release candidates for one movie or episode -- GET /{resource}/{id}/candidates
    -- plus grabbing one -- POST /{resource}/{id}/grab. `resource` is "movies" or
    "episodes". Stateful: load(itemId) remembers which item grab() acts on. The base
    class's sequence guard drops a slow load() reply for an item the user already left;
    grabFinished carries the item id so a page only reacts to its own grab."""

    FIELDS = [
        ("title", "title"),
        ("downloadUrl", "download_url"),
        ("indexerName", "indexer_name", ""),
        ("quality", "quality", ""),
        ("size", "size", 0),
        ("seeders", "seeders", 0),
        ("peers", "peers", 0),
        ("isBest", "is_best", False),
    ]

    grabFinished = Signal(int, bool, str)  # itemId, ok, message
    itemChanged = Signal()

    def __init__(self, api, resource: str, parent=None):
        assert resource in ("movies", "episodes"), resource
        super().__init__(api, parent)
        self._resource = resource
        self._item_id: int | None = None

    currentItemId = Property(int, lambda self: self._item_id or 0, notify=itemChanged)

    @Slot(int)
    def load(self, itemId: int) -> None:
        self._item_id = itemId
        self.itemChanged.emit()
        self._fetch(f"/{self._resource}/{itemId}/candidates")

    @Slot()
    def refresh(self) -> None:
        if self._item_id is not None:
            self.load(self._item_id)

    @Slot(str, str)
    def grab(self, downloadUrl: str, releaseTitle: str) -> None:
        if self._item_id is None:
            self.grabFinished.emit(-1, False, "Nothing loaded")
            return
        item_id = self._item_id

        def on_done(status: int, body) -> None:
            if status in (200, 201):
                self.grabFinished.emit(item_id, True, "Grabbed")
            else:
                self.grabFinished.emit(item_id, False, self.api.error_message(status, body))

        self.api.request("POST", f"/{self._resource}/{item_id}/grab", {"download_url": downloadUrl, "release_title": releaseTitle}, on_done)
