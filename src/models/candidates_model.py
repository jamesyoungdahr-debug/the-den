import json
from typing import Callable

from PySide6.QtCore import QAbstractListModel, QModelIndex, QUrl, Qt, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

_JSON_CONTENT_TYPE = "application/json"


class CandidatesModel(QAbstractListModel):
    """Scored release candidates for one movie or episode -- GET
    /{resource}/{id}/candidates -- plus grabbing one of them -- POST
    /{resource}/{id}/grab. `resource` is "movies" or "episodes"; both share identical
    candidates/grab semantics on the backend, only the URL prefix differs, so one class
    serves both rather than duplicating it. Stateful: load(itemId) remembers which
    movie/episode subsequent grab() calls act on, matching the natural "open this
    item's releases, pick one" UI flow."""

    TitleRole = Qt.ItemDataRole.UserRole + 1
    DownloadUrlRole = Qt.ItemDataRole.UserRole + 2
    IndexerNameRole = Qt.ItemDataRole.UserRole + 3
    QualityRole = Qt.ItemDataRole.UserRole + 4
    SeedersRole = Qt.ItemDataRole.UserRole + 5
    IsBestRole = Qt.ItemDataRole.UserRole + 6

    errorOccurred = Signal(str)
    grabFinished = Signal(int, bool, str)  # itemId, ok, message

    def __init__(self, base_url_provider: Callable[[], str], resource: str, parent=None):
        super().__init__(parent)
        assert resource in ("movies", "episodes"), resource
        self._resource = resource
        self._items: list[dict] = []
        self._manager = QNetworkAccessManager(self)
        self._base_url = base_url_provider
        self._item_id: int | None = None
        # This model is a single shared instance reused across every movie/episode's
        # Releases page (see main.py). Bumped on every load() so a reply from a
        # superseded load (the user navigated to a different item before it returned)
        # can be told apart from the current one and dropped instead of clobbering
        # whatever's now on screen with a different item's data.
        self._request_seq = 0

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        return {
            self.TitleRole: item["title"],
            self.DownloadUrlRole: item["download_url"],
            self.IndexerNameRole: item["indexer_name"],
            self.QualityRole: item["quality"],
            self.SeedersRole: item.get("seeders"),
            self.IsBestRole: item.get("is_best", False),
        }.get(role)

    def roleNames(self):
        return {
            self.TitleRole: b"title",
            self.DownloadUrlRole: b"downloadUrl",
            self.IndexerNameRole: b"indexerName",
            self.QualityRole: b"quality",
            self.SeedersRole: b"seeders",
            self.IsBestRole: b"isBest",
        }

    @Slot(int)
    def load(self, itemId: int) -> None:
        self._item_id = itemId
        self._request_seq += 1
        seq = self._request_seq
        url = f"{self._base_url()}/{self._resource}/{itemId}/candidates"
        reply = self._manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(lambda: self._on_load_reply(reply, seq))

    def _on_load_reply(self, reply: QNetworkReply, seq: int) -> None:
        reply.deleteLater()
        if seq != self._request_seq:
            # A newer load() has already superseded this one (the user opened a
            # different item's page before this reply came back) -- whatever page
            # is showing now isn't for this reply, so drop it rather than reset
            # the model to a different item's candidates or bounce an error onto it.
            return
        if reply.error() == QNetworkReply.NetworkError.NoError:
            body = bytes(reply.readAll().data())
            try:
                items = json.loads(body)
            except json.JSONDecodeError:
                items = []
            self.beginResetModel()
            self._items = items
            self.endResetModel()
        else:
            self.errorOccurred.emit(reply.errorString())

    @Slot(str, str)
    def grab(self, downloadUrl: str, releaseTitle: str) -> None:
        if self._item_id is None:
            self.grabFinished.emit(-1, False, "Nothing loaded")
            return
        item_id = self._item_id
        payload = {"download_url": downloadUrl, "release_title": releaseTitle}
        url = f"{self._base_url()}/{self._resource}/{item_id}/grab"
        request = QNetworkRequest(QUrl(url))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, _JSON_CONTENT_TYPE)
        reply = self._manager.post(request, json.dumps(payload).encode())
        reply.finished.connect(lambda: self._on_grab_reply(reply, item_id))

    def _on_grab_reply(self, reply: QNetworkReply, item_id: int) -> None:
        # itemId travels with the result so a page only reacts to a grab it actually
        # started -- this model is a single shared instance across every item's page
        # (see load()'s docstring note), so without this a slow grab finishing after
        # the user has navigated to a different item would show its result there instead.
        if reply.error() == QNetworkReply.NetworkError.NoError:
            self.grabFinished.emit(item_id, True, "Grabbed")
        else:
            body = bytes(reply.readAll().data()).decode(errors="replace")
            message = f"{reply.errorString()} — {body}" if body else reply.errorString()
            self.grabFinished.emit(item_id, False, message)
        reply.deleteLater()
