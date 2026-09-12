"""Calendar data composed client-side from /movies and /series/{id}/episodes (there is no
JSON calendar endpoint): missing movies, and every episode without a file across the
library, split into "aired but missing" and "upcoming" by air date."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Property, Signal, Slot

from models.base import JsonListModel


class CalendarMoviesModel(JsonListModel):
    """Missing movies -- GET /movies filtered to has_file=false."""

    FIELDS = [("movieId", "id"), ("title", "title"), ("year", "year"), ("posterPath", "poster_path", "")]

    @Slot()
    def refresh(self) -> None:
        self._fetch("/movies", transform=lambda items: [m for m in items if not m.get("has_file")])


class CalendarEpisodesModel(JsonListModel):
    """Episodes without a file across every series: GET /series, then one
    /series/{id}/episodes per series (fan-out, fan-in), flattened with the series title
    and sorted by air date. `upcoming` marks episodes that haven't aired yet."""

    FIELDS = [
        ("episodeId", "id"),
        ("seriesId", "series_id"),
        ("seriesTitle", "series_title", ""),
        ("posterPath", "poster_path", ""),
        ("seasonNumber", "season_number"),
        ("episodeNumber", "episode_number"),
        ("title", "title", ""),
        ("airDate", "air_date", ""),
        ("upcoming", "upcoming", False),
    ]
    statsChanged = Signal()  # own signal: a notify must belong to the declaring class, and re-declaring the base name crashes PySide

    missingCount = Property(int, lambda self: sum(1 for e in self._items if not e.get("upcoming")), notify=statsChanged)
    upcomingCount = Property(int, lambda self: sum(1 for e in self._items if e.get("upcoming")), notify=statsChanged)

    def _set_items(self, items: list[dict]) -> None:
        super()._set_items(items)
        self.statsChanged.emit()

    @Slot()
    def refresh(self) -> None:
        self._seq += 1
        seq = self._seq
        self._set_loading(True)

        def on_series(status: int, body) -> None:
            if seq != self._seq:
                return
            if status != 200 or not isinstance(body, list):
                self._set_loading(False)
                self.errorOccurred.emit(self.api.error_message(status, body))
                return
            series_list = body
            if not series_list:
                self._set_loading(False)
                self._set_items([])
                return
            pending = {"n": len(series_list)}
            collected: list[dict] = []
            today = date.today().isoformat()

            def make_handler(series: dict):
                def on_episodes(st: int, eps) -> None:
                    if seq != self._seq:
                        return
                    if st == 200 and isinstance(eps, list):
                        for ep in eps:
                            if not ep.get("has_file"):
                                air = ep.get("air_date") or ""
                                collected.append({**ep, "series_title": series["title"], "poster_path": series.get("poster_path") or "",
                                                  "upcoming": bool(air) and air > today})
                    pending["n"] -= 1
                    if pending["n"] == 0:
                        collected.sort(key=lambda e: (e.get("air_date") or "9999", e["season_number"], e["episode_number"]))
                        self._set_loading(False)
                        self._set_items(collected)
                return on_episodes

            for series in series_list:
                self.api.request("GET", f"/series/{series['id']}/episodes", on_done=make_handler(series))

        self.api.request("GET", "/series", on_done=on_series)
