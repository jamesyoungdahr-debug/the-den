from PySide6.QtCore import QUrl, Slot

from models.base import JsonListModel


class SeriesListModel(JsonListModel):
    """The TV library -- GET/POST/DELETE /series."""

    PATH = "/series"
    FIELDS = [
        ("seriesId", "id"),
        ("tvmazeId", "tvmaze_id"),
        ("tmdbId", "tmdb_id"),
        ("title", "title"),
        ("year", "year"),
        ("overview", "overview", ""),
        ("posterPath", "poster_path", ""),
    ]

    @Slot(int, str, str, str, str)
    def addSeries(self, tvmazeId: int, title: str, year: str, overview: str, posterPath: str) -> None:
        payload: dict = {"tvmaze_id": tvmazeId, "title": title}
        if year:
            payload["year"] = int(year)
        if overview:
            payload["overview"] = overview
        if posterPath:
            payload["poster_path"] = posterPath
        self._write("POST", "/series", payload)

    @Slot(int)
    def deleteSeries(self, seriesId: int) -> None:
        self._write("DELETE", f"/series/{seriesId}")


class SeriesSearchResultsModel(JsonListModel):
    """Ephemeral TVmaze search results (GET /series/search-tvmaze) for the add flow."""

    FIELDS = [
        ("tvmazeId", "tvmaze_id"),
        ("title", "title"),
        ("year", "year"),
        ("overview", "overview", ""),
        ("posterPath", "poster_path", ""),
    ]

    @Slot(str)
    def search(self, query: str) -> None:
        if not query.strip():
            self._set_items([])
            return
        self._fetch(f"/series/search-tvmaze?q={QUrl.toPercentEncoding(query).data().decode()}")

    @Slot()
    def clear(self) -> None:
        self._set_items([])
