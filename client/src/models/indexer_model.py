import json
from typing import Callable

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QUrl, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

_JSON_CONTENT_TYPE = "application/json"


class IndexerListModel(QAbstractListModel):
    """Backed by GET/POST/DELETE /indexers and GET /indexers/{id}/test on the backend.
    All requests go through QNetworkAccessManager (async, never blocks the UI thread)."""

    IdRole = Qt.ItemDataRole.UserRole + 1
    NameRole = Qt.ItemDataRole.UserRole + 2
    UrlRole = Qt.ItemDataRole.UserRole + 3
    ProtocolRole = Qt.ItemDataRole.UserRole + 4
    EnabledRole = Qt.ItemDataRole.UserRole + 5

    errorOccurred = Signal(str)
    testResult = Signal(int, bool, str)  # indexer id, ok, message

    def __init__(self, base_url_provider: Callable[[], str], parent=None):
        super().__init__(parent)
        self._items: list[dict] = []
        self._manager = QNetworkAccessManager(self)
        self._base_url = base_url_provider  # callable so it always reflects the current server URL

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        return {
            self.IdRole: item["id"],
            self.NameRole: item["name"],
            self.UrlRole: item["url"],
            self.ProtocolRole: item["protocol"],
            self.EnabledRole: item["enabled"],
        }.get(role)

    def roleNames(self):
        return {
            self.IdRole: b"indexerId",
            self.NameRole: b"name",
            self.UrlRole: b"url",
            self.ProtocolRole: b"protocol",
            # Named "indexerEnabled", not "enabled" -- every QML Item already has a
            # built-in "enabled" property, and a model role of that name would collide
            # with it in delegate scope rather than cleanly injecting.
            self.EnabledRole: b"indexerEnabled",
        }

    @Slot()
    def refresh(self) -> None:
        reply = self._manager.get(QNetworkRequest(QUrl(f"{self._base_url()}/indexers")))
        reply.finished.connect(lambda: self._on_list_reply(reply))

    def _on_list_reply(self, reply: QNetworkReply) -> None:
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
        reply.deleteLater()

    @Slot(str, str, str, str)
    def addIndexer(self, name: str, url: str, apiKey: str, protocol: str) -> None:
        payload = {"name": name, "url": url, "protocol": protocol or "torznab"}
        if apiKey:
            payload["api_key"] = apiKey
        request = QNetworkRequest(QUrl(f"{self._base_url()}/indexers"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, _JSON_CONTENT_TYPE)
        reply = self._manager.post(request, json.dumps(payload).encode())
        reply.finished.connect(lambda: self._on_write_reply(reply))

    @Slot(int)
    def deleteIndexer(self, indexer_id: int) -> None:
        reply = self._manager.deleteResource(QNetworkRequest(QUrl(f"{self._base_url()}/indexers/{indexer_id}")))
        reply.finished.connect(lambda: self._on_write_reply(reply))

    def _on_write_reply(self, reply: QNetworkReply) -> None:
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.errorOccurred.emit(reply.errorString())
        reply.deleteLater()
        self.refresh()

    @Slot(int)
    def testIndexer(self, indexer_id: int) -> None:
        reply = self._manager.get(QNetworkRequest(QUrl(f"{self._base_url()}/indexers/{indexer_id}/test")))
        reply.finished.connect(lambda: self._on_test_reply(indexer_id, reply))

    def _on_test_reply(self, indexer_id: int, reply: QNetworkReply) -> None:
        ok = reply.error() == QNetworkReply.NetworkError.NoError
        body = bytes(reply.readAll().data()).decode(errors="replace")
        message = body if ok else f"{reply.errorString()} — {body}" if body else reply.errorString()
        reply.deleteLater()
        self.testResult.emit(indexer_id, ok, message)
