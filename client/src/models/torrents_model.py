"""The built-in torrent client's live view -- GET /torrents (+ /torrents/engine), with
pause / resume / remove / add-by-hand. Polls while a page asks it to (`polling`)."""

from __future__ import annotations

from PySide6.QtCore import Property, QTimer, Signal, Slot

from models.base import JsonListModel


class TorrentsModel(JsonListModel):
    PATH = "/torrents"
    FIELDS = [
        ("infoHash", "info_hash"),
        ("name", "name", ""),
        ("label", "label", ""),
        ("state", "state", ""),
        ("progress", "progress", 0.0),
        ("totalSize", "total_size", 0),
        ("downloaded", "downloaded", 0),
        ("uploaded", "uploaded", 0),
        ("downloadRate", "download_rate", 0),
        ("uploadRate", "upload_rate", 0),
        ("numPeers", "num_peers", 0),
        ("numSeeds", "num_seeds", 0),
        ("etaSeconds", "eta_seconds", -1),
        ("ratio", "ratio", 0.0),
        ("isFinished", "is_finished", False),
        ("error", "error", ""),
        ("recordStatus", "record_status", ""),
        ("group", "group", "active"),
    ]

    engineChanged = Signal()
    pollingChanged = Signal()
    addFinished = Signal(bool, str)
    statsChanged = Signal()  # own signal: a notify must belong to the declaring class, and re-declaring the base name crashes PySide

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._engine: dict = {}
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self.refresh)

    def _set_items(self, items: list[dict]) -> None:
        super()._set_items(items)
        self.statsChanged.emit()

    engine = Property("QVariantMap", lambda self: dict(self._engine), notify=engineChanged)
    downloadRate = Property(int, lambda self: sum(int(t.get("download_rate") or 0) for t in self._items), notify=statsChanged)
    uploadRate = Property(int, lambda self: sum(int(t.get("upload_rate") or 0) for t in self._items), notify=statsChanged)
    activeCount = Property(int, lambda self: sum(1 for t in self._items if t.get("group") == "active"), notify=statsChanged)
    seedingCount = Property(int, lambda self: sum(1 for t in self._items if t.get("group") == "seeding"), notify=statsChanged)

    def _get_polling(self) -> bool:
        return self._timer.isActive()

    def _set_polling(self, value: bool) -> None:
        if value and not self._timer.isActive():
            self._timer.start()
            self.refresh()
            self.pollingChanged.emit()
        elif not value and self._timer.isActive():
            self._timer.stop()
            self.pollingChanged.emit()

    polling = Property(bool, _get_polling, _set_polling, notify=pollingChanged)

    @staticmethod
    def _group(t: dict) -> str:
        state = t.get("state") or ""
        if state in ("paused", "stopped") or t.get("error"):
            return "stopped"
        if t.get("is_finished") or state in ("seeding", "finished"):
            return "seeding"
        return "active"

    @Slot()
    def refresh(self) -> None:
        order = {"active": 0, "seeding": 1, "stopped": 2}
        self._fetch("/torrents", transform=lambda items: sorted(
            ({**t, "group": self._group(t)} for t in items), key=lambda t: (order[t["group"]], -(t.get("added_at") or 0))))

        def on_engine(status: int, body) -> None:
            if status == 200 and isinstance(body, dict):
                self._engine = body
                self.engineChanged.emit()

        self.api.request("GET", "/torrents/engine", on_done=on_engine)

    @Slot(str)
    def pause(self, infoHash: str) -> None:
        self._write("POST", f"/torrents/{infoHash}/pause")

    @Slot(str)
    def resume(self, infoHash: str) -> None:
        self._write("POST", f"/torrents/{infoHash}/resume")

    @Slot(str, bool)
    def remove(self, infoHash: str, deleteFiles: bool) -> None:
        self._write("DELETE", f"/torrents/{infoHash}?delete_files={'true' if deleteFiles else 'false'}")

    @Slot(str)
    def add(self, source: str) -> None:
        def on_done(status: int, body) -> None:
            if status == 201:
                self.addFinished.emit(True, f"Added {body.get('name') or 'torrent'}" if isinstance(body, dict) else "Added")
            else:
                self.addFinished.emit(False, self.api.error_message(status, body))
            self.refresh()

        self.api.request("POST", "/torrents", {"source": source.strip()}, on_done)
