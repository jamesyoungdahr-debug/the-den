from PySide6.QtCore import Property, Signal, Slot

from models.base import JsonListModel


class EpisodesModel(JsonListModel):
    """Episodes for one series -- GET /series/{id}/episodes. load(seriesId) remembers the
    series so refresh() after a grab reloads the same list."""

    FIELDS = [
        ("episodeId", "id"),
        ("seriesId", "series_id"),
        ("seasonNumber", "season_number"),
        ("episodeNumber", "episode_number"),
        ("title", "title", ""),
        ("airDate", "air_date", ""),
        ("hasFile", "has_file", False),
    ]

    seriesChanged = Signal()
    # A Property's notify must be a signal declared on the same class (a base-class
    # signal, or re-declaring the base's name, crashes PySide's property cache), so
    # derived stats get their own signal, emitted after every reset.
    statsChanged = Signal()

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._series_id: int | None = None

    def _set_items(self, items: list[dict]) -> None:
        super()._set_items(items)
        self.statsChanged.emit()

    currentSeriesId = Property(int, lambda self: self._series_id or 0, notify=seriesChanged)
    haveCount = Property(int, lambda self: sum(1 for e in self._items if e.get("has_file")), notify=statsChanged)

    @Slot(int)
    def load(self, seriesId: int) -> None:
        self._series_id = seriesId
        self.seriesChanged.emit()
        self._fetch(f"/series/{seriesId}/episodes")

    @Slot()
    def refresh(self) -> None:
        if self._series_id is not None:
            self._fetch(f"/series/{self._series_id}/episodes")
