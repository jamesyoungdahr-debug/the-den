import json
from typing import Callable

from PySide6.QtCore import QAbstractListModel, QModelIndex, QUrl, Qt, Signal, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

# There's no JSON /calendar endpoint on the backend (only the HTML page), so these
# compose the calendar view client-side from the already-tested /movies and
# /series/{id}/episodes endpoints, filtering to has_file=false -- rather than expand
# the backend's API surface for one screen.


class CalendarMoviesModel(QAbstractListModel):
    """Missing movies -- GET /movies, filtered to has_file=false."""

    TitleRole = Qt.ItemDataRole.UserRole + 1
    YearRole = Qt.ItemDataRole.UserRole + 2

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
        return {self.TitleRole: item["title"], self.YearRole: item.get("year")}.get(role)

    def roleNames(self):
        return {self.TitleRole: b"title", self.YearRole: b"year"}

    @Slot()
    def refresh(self) -> None:
        reply = self._manager.get(QNetworkRequest(QUrl(f"{self._base_url()}/movies")))
        reply.finished.connect(lambda: self._on_reply(reply))

    def _on_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            body = bytes(reply.readAll().data())
            try:
                items = json.loads(body)
            except json.JSONDecodeError:
                items = []
            self.beginResetModel()
            self._items = [m for m in items if not m.get("has_file")]
            self.endResetModel()
        else:
            self.errorOccurred.emit(reply.errorString())
        reply.deleteLater()


class CalendarEpisodesModel(QAbstractListModel):
    """Missing episodes across every series in the library -- GET /series, then GET
    /series/{id}/episodes for each, filtered to has_file=false and flattened with the
    series title attached to each row. A fan-out/fan-in over N+1 requests: fires one
    episodes request per series, waits for all of them, then builds the combined,
    date-sorted list in one go."""

    SeriesTitleRole = Qt.ItemDataRole.UserRole + 1
    SeasonNumberRole = Qt.ItemDataRole.UserRole + 2
    EpisodeNumberRole = Qt.ItemDataRole.UserRole + 3
    TitleRole = Qt.ItemDataRole.UserRole + 4
    AirDateRole = Qt.ItemDataRole.UserRole + 5

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
            self.SeriesTitleRole: item["series_title"],
            self.SeasonNumberRole: item["season_number"],
            self.EpisodeNumberRole: item["episode_number"],
            self.TitleRole: item.get("title") or "",
            self.AirDateRole: item.get("air_date") or "",
        }.get(role)

    def roleNames(self):
        return {
            self.SeriesTitleRole: b"seriesTitle",
            self.SeasonNumberRole: b"seasonNumber",
            self.EpisodeNumberRole: b"episodeNumber",
            self.TitleRole: b"title",
            self.AirDateRole: b"airDate",
        }

    @Slot()
    def refresh(self) -> None:
        reply = self._manager.get(QNetworkRequest(QUrl(f"{self._base_url()}/series")))
        reply.finished.connect(lambda: self._on_series_reply(reply))

    def _on_series_reply(self, reply: QNetworkReply) -> None:
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.errorOccurred.emit(reply.errorString())
            reply.deleteLater()
            return
        body = bytes(reply.readAll().data())
        reply.deleteLater()
        try:
            series_list = json.loads(body)
        except json.JSONDecodeError:
            series_list = []

        if not series_list:
            self.beginResetModel()
            self._items = []
            self.endResetModel()
            return

        pending = len(series_list)
        collected: list[dict] = []

        def on_episodes_reply(series_title: str, ep_reply: QNetworkReply) -> None:
            nonlocal pending
            if ep_reply.error() == QNetworkReply.NetworkError.NoError:
                ep_body = bytes(ep_reply.readAll().data())
                try:
                    episodes = json.loads(ep_body)
                except json.JSONDecodeError:
                    episodes = []
                for ep in episodes:
                    if not ep.get("has_file"):
                        collected.append({**ep, "series_title": series_title})
            ep_reply.deleteLater()
            pending -= 1
            if pending == 0:
                collected.sort(key=lambda e: e.get("air_date") or "")
                self.beginResetModel()
                self._items = collected
                self.endResetModel()

        for series in series_list:
            url = f"{self._base_url()}/series/{series['id']}/episodes"
            ep_reply = self._manager.get(QNetworkRequest(QUrl(url)))
            ep_reply.finished.connect(lambda r=ep_reply, t=series["title"]: on_episodes_reply(t, r))
