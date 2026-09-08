import json
from typing import Callable

from PySide6.QtCore import QAbstractListModel, QModelIndex, QUrl, Qt, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class EpisodesModel(QAbstractListModel):
    """Episodes for one series -- GET /series/{id}/episodes. Stateful: load(seriesId)
    remembers the series for a possible future refresh() call, matching EpisodesPage's
    "open a series, see its episodes" flow."""

    EpisodeIdRole = Qt.ItemDataRole.UserRole + 1
    SeasonNumberRole = Qt.ItemDataRole.UserRole + 2
    EpisodeNumberRole = Qt.ItemDataRole.UserRole + 3
    TitleRole = Qt.ItemDataRole.UserRole + 4
    HasFileRole = Qt.ItemDataRole.UserRole + 5

    errorOccurred = Signal(str)

    def __init__(self, base_url_provider: Callable[[], str], parent=None):
        super().__init__(parent)
        self._items: list[dict] = []
        self._manager = QNetworkAccessManager(self)
        self._base_url = base_url_provider
        self._series_id: int | None = None

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        return {
            self.EpisodeIdRole: item["id"],
            self.SeasonNumberRole: item["season_number"],
            self.EpisodeNumberRole: item["episode_number"],
            self.TitleRole: item.get("title") or "",
            self.HasFileRole: item["has_file"],
        }.get(role)

    def roleNames(self):
        return {
            self.EpisodeIdRole: b"episodeId",
            self.SeasonNumberRole: b"seasonNumber",
            self.EpisodeNumberRole: b"episodeNumber",
            self.TitleRole: b"title",
            self.HasFileRole: b"hasFile",
        }

    @Slot(int)
    def load(self, seriesId: int) -> None:
        self._series_id = seriesId
        reply = self._manager.get(QNetworkRequest(QUrl(f"{self._base_url()}/series/{seriesId}/episodes")))
        reply.finished.connect(lambda: self._on_load_reply(reply))

    def _on_load_reply(self, reply: QNetworkReply) -> None:
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
