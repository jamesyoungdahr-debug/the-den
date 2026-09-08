import json
from typing import Callable

from PySide6.QtCore import QAbstractListModel, QModelIndex, QUrl, QUrlQuery, Qt, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

_JSON_CONTENT_TYPE = "application/json"


class SeriesListModel(QAbstractListModel):
    """The TV library -- backed by GET/POST/DELETE /series on the backend."""

    SeriesIdRole = Qt.ItemDataRole.UserRole + 1
    TitleRole = Qt.ItemDataRole.UserRole + 2
    YearRole = Qt.ItemDataRole.UserRole + 3

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
            self.SeriesIdRole: item["id"],
            self.TitleRole: item["title"],
            self.YearRole: item.get("year"),
        }.get(role)

    def roleNames(self):
        return {
            self.SeriesIdRole: b"seriesId",
            self.TitleRole: b"title",
            self.YearRole: b"year",
        }

    @Slot()
    def refresh(self) -> None:
        reply = self._manager.get(QNetworkRequest(QUrl(f"{self._base_url()}/series")))
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

    @Slot(int, str, str, str, str)
    def addSeries(self, tvmazeId: int, title: str, year: str, overview: str, posterPath: str) -> None:
        payload = {"tvmaze_id": tvmazeId, "title": title}
        if year:
            payload["year"] = int(year)
        if overview:
            payload["overview"] = overview
        if posterPath:
            payload["poster_path"] = posterPath
        request = QNetworkRequest(QUrl(f"{self._base_url()}/series"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, _JSON_CONTENT_TYPE)
        reply = self._manager.post(request, json.dumps(payload).encode())
        reply.finished.connect(lambda: self._on_write_reply(reply))

    @Slot(int)
    def deleteSeries(self, seriesId: int) -> None:
        reply = self._manager.deleteResource(QNetworkRequest(QUrl(f"{self._base_url()}/series/{seriesId}")))
        reply.finished.connect(lambda: self._on_write_reply(reply))

    def _on_write_reply(self, reply: QNetworkReply) -> None:
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.errorOccurred.emit(reply.errorString())
        reply.deleteLater()
        self.refresh()


class SeriesSearchResultsModel(QAbstractListModel):
    """Ephemeral TVmaze search results (GET /series/search-tvmaze) -- separate from
    the library itself, same split as MovieSearchResultsModel."""

    TvmazeIdRole = Qt.ItemDataRole.UserRole + 1
    TitleRole = Qt.ItemDataRole.UserRole + 2
    YearRole = Qt.ItemDataRole.UserRole + 3
    OverviewRole = Qt.ItemDataRole.UserRole + 4
    PosterPathRole = Qt.ItemDataRole.UserRole + 5

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
            self.TvmazeIdRole: item["tvmaze_id"],
            self.TitleRole: item["title"],
            self.YearRole: item.get("year"),
            self.OverviewRole: item.get("overview") or "",
            self.PosterPathRole: item.get("poster_path") or "",
        }.get(role)

    def roleNames(self):
        return {
            self.TvmazeIdRole: b"tvmazeId",
            self.TitleRole: b"title",
            self.YearRole: b"year",
            self.OverviewRole: b"overview",
            self.PosterPathRole: b"posterPath",
        }

    @Slot(str)
    def search(self, query: str) -> None:
        url = QUrl(f"{self._base_url()}/series/search-tvmaze")
        q = QUrlQuery()
        q.addQueryItem("q", query)
        url.setQuery(q)
        reply = self._manager.get(QNetworkRequest(url))
        reply.finished.connect(lambda: self._on_search_reply(reply))

    def _on_search_reply(self, reply: QNetworkReply) -> None:
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
