from PySide6.QtCore import Slot

from models.base import JsonListModel


class MovieListModel(JsonListModel):
    """The movie library -- GET/POST/DELETE /movies."""

    PATH = "/movies"
    FIELDS = [
        ("movieId", "id"),
        ("tmdbId", "tmdb_id"),
        ("title", "title"),
        ("year", "year"),
        ("overview", "overview", ""),
        ("posterPath", "poster_path", ""),
        ("hasFile", "has_file", False),
    ]

    @Slot(int, str, str, str, str)
    def addMovie(self, tmdbId: int, title: str, year: str, overview: str, posterPath: str) -> None:
        payload: dict = {"tmdb_id": tmdbId, "title": title}
        if year:
            payload["year"] = int(year)
        if overview:
            payload["overview"] = overview
        if posterPath:
            payload["poster_path"] = posterPath
        self._write("POST", "/movies", payload)

    @Slot(int)
    def deleteMovie(self, movieId: int) -> None:
        self._write("DELETE", f"/movies/{movieId}")


class MovieSearchResultsModel(JsonListModel):
    """Ephemeral TMDB search results (GET /movies/search-tmdb) for the add flow."""

    FIELDS = [
        ("tmdbId", "tmdb_id"),
        ("title", "title"),
        ("year", "year"),
        ("overview", "overview", ""),
        ("posterPath", "poster_path", ""),
    ]

    @Slot(str)
    def search(self, query: str) -> None:
        from PySide6.QtCore import QUrl
        if not query.strip():
            self._set_items([])
            return
        self._fetch(f"/movies/search-tmdb?q={QUrl.toPercentEncoding(query).data().decode()}")

    @Slot()
    def clear(self) -> None:
        self._set_items([])
