import json
from typing import Callable

from PySide6.QtCore import QAbstractListModel, QModelIndex, QUrl, Qt, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class DownloadsModel(QAbstractListModel):
    """Backed by GET /downloads and POST /downloads/{id}/check on the backend."""

    DownloadIdRole = Qt.ItemDataRole.UserRole + 1
    ReleaseTitleRole = Qt.ItemDataRole.UserRole + 2
    StatusRole = Qt.ItemDataRole.UserRole + 3

    errorOccurred = Signal(str)

    def __init__(self, base_url_provider: Callable[[], str], parent=None):
        super().__init__(parent)
        self._items: list[dict] = []
        self._manager = QNetworkAccessManager(self)
        self._base_url = base_url_provider

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        return {
            self.DownloadIdRole: item["id"],
            self.ReleaseTitleRole: item["release_title"],
            self.StatusRole: item["status"],
        }.get(role)

    def roleNames(self):
        return {
            self.DownloadIdRole: b"downloadId",
            self.ReleaseTitleRole: b"releaseTitle",
            self.StatusRole: b"status",
        }

    @Slot()
    def refresh(self) -> None:
        reply = self._manager.get(QNetworkRequest(QUrl(f"{self._base_url()}/downloads")))
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

    @Slot(int)
    def check(self, downloadId: int) -> None:
        reply = self._manager.post(
            QNetworkRequest(QUrl(f"{self._base_url()}/downloads/{downloadId}/check")), b""
        )
        reply.finished.connect(lambda: self._on_check_reply(reply))

    def _on_check_reply(self, reply: QNetworkReply) -> None:
        if reply.error() != QNetworkReply.NetworkError.NoError:
            body = bytes(reply.readAll().data()).decode(errors="replace")
            message = f"{reply.errorString()} — {body}" if body else reply.errorString()
            self.errorOccurred.emit(message)
        reply.deleteLater()
        self.refresh()
