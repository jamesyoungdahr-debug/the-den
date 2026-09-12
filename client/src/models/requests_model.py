"""Requests (U4): GET /api/requests with a status filter; approve / decline / withdraw."""

from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot

from models.base import JsonListModel


class RequestsModel(JsonListModel):
    FIELDS = [
        ("requestId", "id"),
        ("mediaType", "media_type"),
        ("tmdbId", "tmdb_id"),
        ("title", "title"),
        ("year", "year"),
        ("posterPath", "poster_path", ""),
        ("seasons", "seasons", []),
        ("seasonsLabel", "seasons_label", ""),
        ("status", "status", ""),
        ("displayStatus", "display_status", ""),
        ("note", "note", ""),
        ("requester", "requester", ""),
        ("requesterInitial", "requester_initial", ""),
        ("requesterId", "requester_id", 0),
        ("decidedBy", "decided_by", ""),
        ("createdAt", "created_at", ""),
        ("availableAt", "available_at", ""),
        ("seriesId", "series_id", 0),
        ("movieId", "movie_id", 0),
    ]

    filterChanged = Signal()
    pendingChanged = Signal()
    actionFinished = Signal(bool, str)

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._filter = "all"
        self._pending = 0

    def _get_filter(self) -> str:
        return self._filter

    def _set_filter(self, value: str) -> None:
        if value != self._filter:
            self._filter = value
            self.filterChanged.emit()
            self.refresh()

    filter = Property(str, _get_filter, _set_filter, notify=filterChanged)
    pendingCount = Property(int, lambda self: self._pending, notify=pendingChanged)

    @staticmethod
    def _flatten(items: list[dict]) -> list[dict]:
        out = []
        for r in items:
            who = r.get("requested_by") or {}
            seasons = r.get("seasons") or []
            out.append({
                **r,
                "requester": who.get("username") or "",
                "requester_initial": who.get("initial") or "?",
                "requester_id": who.get("id") or 0,
                "seasons_label": " ".join(f"S{int(n):02d}" for n in seasons),
                "decided_by": r.get("decided_by") or "",
            })
        return out

    @Slot()
    def refresh(self) -> None:
        query = "" if self._filter == "all" else f"?status={self._filter}"
        self._fetch(f"/api/requests{query}", transform=self._flatten)
        self.refreshPending()

    @Slot()
    def refreshPending(self) -> None:
        def on_done(status: int, body) -> None:
            if status == 200 and isinstance(body, list):
                if len(body) != self._pending:
                    self._pending = len(body)
                    self.pendingChanged.emit()
            elif status in (401, 403) and self._pending:
                self._pending = 0
                self.pendingChanged.emit()

        self.api.request("GET", "/api/requests?status=pending", on_done=on_done)

    def _act(self, method: str, path: str, payload: dict | None, success: str) -> None:
        def on_done(status: int, body) -> None:
            ok = status in (200, 201, 204)
            self.actionFinished.emit(ok, success if ok else self.api.error_message(status, body))
            self.refresh()

        self.api.request(method, path, payload, on_done)

    @Slot(int)
    def approve(self, requestId: int) -> None:
        self._act("POST", f"/api/requests/{requestId}/approve", None, "Approved")

    @Slot(int, str)
    def decline(self, requestId: int, note: str) -> None:
        self._act("POST", f"/api/requests/{requestId}/decline", {"note": note or None}, "Declined")

    @Slot(int)
    def remove(self, requestId: int) -> None:
        self._act("DELETE", f"/api/requests/{requestId}", None, "Request withdrawn")
